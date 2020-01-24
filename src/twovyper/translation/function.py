"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from functools import reduce
from itertools import chain, zip_longest
from typing import List

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.nodes import VyperFunction, VyperVar

from twovyper.translation import helpers, mangled, State
from twovyper.translation.context import Context
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.allocation import AllocationTranslator
from twovyper.translation.balance import BalanceTranslator
from twovyper.translation.expression import ExpressionTranslator
from twovyper.translation.model import ModelTranslator
from twovyper.translation.resource import ResourceTranslator
from twovyper.translation.specification import SpecificationTranslator
from twovyper.translation.state import StateTranslator
from twovyper.translation.statement import StatementTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.verification import rules
from twovyper.verification.error import Via

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Method, StmtsAndExpr, Stmt, Expr


class FunctionTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.allocation_translator = AllocationTranslator(viper_ast)
        self.balance_translator = BalanceTranslator(viper_ast)
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.model_translator = ModelTranslator(viper_ast)
        self.resource_translator = ResourceTranslator(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)
        self.statement_translator = StatementTranslator(viper_ast)
        self.state_translator = StateTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def translate(self, function: VyperFunction, ctx: Context) -> Method:
        with ctx.function_scope():
            # A synthesized __init__ does not have a position in the file
            if function.node:
                pos = self.to_position(function.node, ctx)
            else:
                pos = self.to_position(ctx.program.node, ctx)

            ctx.function = function
            is_init = (function.name == names.INIT)

            args = {name: self._translate_var(var, ctx) for name, var in function.args.items()}
            # Local variables will be added when translating.
            locals = {}
            # The msg variable
            locals[names.MSG] = TranslatedVar(names.MSG, mangled.MSG, types.MSG_TYPE, self.viper_ast)
            # The block variable
            locals[names.BLOCK] = TranslatedVar(names.BLOCK, mangled.BLOCK, types.BLOCK_TYPE, self.viper_ast)
            # The chain variable
            locals[names.CHAIN] = TranslatedVar(names.CHAIN, mangled.CHAIN, types.CHAIN_TYPE, self.viper_ast)
            # The tx variable
            locals[names.TX] = TranslatedVar(names.TX, mangled.TX, types.TX_TYPE, self.viper_ast)

            # We represent self as a struct in each state (present, old, pre, issued).
            # For other contracts we use a map from addresses to structs.

            ctx.present_state = self.state_translator.state(mangled.present_state_var_name, ctx)
            # The last publicly visible state of the blockchain
            ctx.old_state = self.state_translator.state(mangled.old_state_var_name, ctx)
            # The state of the blockchain before the function call
            ctx.pre_state = self.state_translator.state(mangled.pre_state_var_name, ctx)
            # The state of the blockchain when the transaction was issued
            ctx.issued_state = self.state_translator.state(mangled.issued_state_var_name, ctx)
            # Usually self refers to the present state and old(self) refers to the old state
            ctx.current_state = ctx.present_state
            ctx.current_old_state = ctx.old_state
            # We create copies of variable maps because ctx is allowed to modify them
            ctx.args = args.copy()
            ctx.locals = locals.copy()

            state_dicts = [ctx.present_state, ctx.old_state, ctx.pre_state, ctx.issued_state]
            state = []
            for d in state_dicts:
                state.extend(d.values())

            self_var = ctx.self_var.local_var(ctx)
            pre_self_var = ctx.pre_self_var.local_var(ctx)

            ctx.success_var = TranslatedVar(names.SUCCESS, mangled.SUCCESS_VAR, types.VYPER_BOOL, self.viper_ast)
            rets = [ctx.success_var]
            success_var = ctx.success_var.local_var(ctx)

            end_label = self.viper_ast.Label(mangled.END_LABEL)
            return_label = self.viper_ast.Label(mangled.RETURN_LABEL)
            revert_label = self.viper_ast.Label(mangled.REVERT_LABEL)

            ctx.return_label = mangled.RETURN_LABEL
            ctx.revert_label = mangled.REVERT_LABEL

            if function.type.return_type:
                ctx.result_var = TranslatedVar(names.RESULT, mangled.RESULT_VAR, function.type.return_type, self.viper_ast)
                rets.append(ctx.result_var)

            body = []

            def assume_type_assumptions(state: State, name: str) -> List[Stmt]:
                stmts = []
                for state_var in state.values():
                    assumptions = self.type_translator.type_assumptions(state_var.local_var(ctx), state_var.type, ctx)
                    stmts.extend(self.viper_ast.Inhale(inv) for inv in assumptions)

                return self.seqn_with_info(stmts, f"{name} state assumptions")

            # Assume type assumptions for self state
            body.extend(assume_type_assumptions(ctx.present_state, "Present"))

            # Assume type assumptions for issued state
            if function.analysis.uses_issued:
                body.extend(assume_type_assumptions(ctx.issued_state, "Issued"))

            # Assume type assumptions for self address
            self_address = helpers.self_address(self.viper_ast)
            self_address_ass = self.type_translator.type_assumptions(self_address, types.VYPER_ADDRESS, ctx)
            self_address_assumptions = [self.viper_ast.Inhale(c) for c in self_address_ass]
            self_address_info_msg = "Assume type assumptions for self address"
            body.extend(self.seqn_with_info(self_address_assumptions, self_address_info_msg))

            # Assume type assumptions for arguments
            argument_conds = []
            for var in function.args.values():
                local_var = args[var.name].local_var(ctx)
                assumptions = self.type_translator.type_assumptions(local_var, var.type, ctx)
                argument_conds.extend(assumptions)

            argument_cond_assumes = [self.viper_ast.Inhale(c) for c in argument_conds]
            ui_info_msg = "Assume type assumptions for arguments"
            body.extend(self.seqn_with_info(argument_cond_assumes, ui_info_msg))

            # Assume type assumptions for block
            block_var = ctx.block_var.local_var(ctx)
            block_conds = self.type_translator.type_assumptions(block_var, types.BLOCK_TYPE, ctx)
            block_assumes = [self.viper_ast.Inhale(c) for c in block_conds]
            block_info_msg = "Assume type assumptions for block"
            body.extend(self.seqn_with_info(block_assumes, block_info_msg))

            # Assume type assumptions for msg
            msg_var = ctx.msg_var.local_var(ctx)
            msg_conds = self.type_translator.type_assumptions(msg_var, types.MSG_TYPE, ctx)
            # We additionally know that msg.sender != 0
            zero = self.viper_ast.IntLit(0)
            msg_sender = helpers.msg_sender(self.viper_ast, ctx)
            neq0 = self.viper_ast.NeCmp(msg_sender, zero)
            msg_assumes = [self.viper_ast.Inhale(c) for c in chain(msg_conds, [neq0])]
            msg_info_msg = "Assume type assumptions for msg"
            body.extend(self.seqn_with_info(msg_assumes, msg_info_msg))

            # Assume unchecked and user-specified invariants
            inv_pres_issued = []
            inv_pres_self = []

            # Translate the invariants for the issued state. Since we don't know anything about
            # the state before then, we use the issued state itself as the old state
            if not is_init and function.analysis.uses_issued:
                with ctx.state_scope(ctx.issued_state, ctx.issued_state):
                    for inv in ctx.unchecked_invariants():
                        inv_pres_issued.append(self.viper_ast.Inhale(inv))

                    for inv in ctx.program.invariants:
                        ppos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        stmts, expr = self.specification_translator.translate_invariant(inv, ctx, True)
                        inv_pres_issued.extend(stmts)
                        inv_pres_issued.append(self.viper_ast.Inhale(expr, ppos))

            # If we use issued, we translate the invariants for the current state with the
            # issued state as the old state, else we just use the self state as the old state
            # which results in fewer assumptions passed to the prover
            if not is_init:
                last_state = ctx.issued_state if function.analysis.uses_issued else ctx.present_state
                with ctx.state_scope(ctx.present_state, last_state):
                    for inv in ctx.unchecked_invariants():
                        inv_pres_self.append(self.viper_ast.Inhale(inv))

                    for inv in ctx.program.invariants:
                        ppos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        stmts, expr = self.specification_translator.translate_invariant(inv, ctx)
                        inv_pres_self.extend(stmts)
                        inv_pres_self.append(self.viper_ast.Inhale(expr, ppos))

            iv_info_msg = "Assume invariants for issued self"
            body.extend(self.seqn_with_info(inv_pres_issued, iv_info_msg))
            iv_info_msg = "Assume invariants for self"
            body.extend(self.seqn_with_info(inv_pres_self, iv_info_msg))

            # old_self and pre_self are the same as self in the beginning
            copy_old = self.state_translator.copy_state(ctx.present_state, ctx.old_state, ctx)
            copy_pre = self.state_translator.copy_state(ctx.present_state, ctx.pre_state, ctx)
            body.extend(copy_old)
            body.extend(copy_pre)

            def returnBool(value: bool) -> Stmt:
                lit = self.viper_ast.TrueLit if value else self.viper_ast.FalseLit
                return self.viper_ast.LocalVarAssign(success_var, lit())

            # If we do not encounter an exception we will return success
            body.append(returnBool(True))

            # Add variable for success(if_not=overflow) that tracks whether an overflow happened
            overflow_var = helpers.overflow_var(self.viper_ast)
            ctx.new_local_vars.append(overflow_var)
            overflow_var_assign = self.viper_ast.LocalVarAssign(overflow_var.localVar(), self.viper_ast.FalseLit())
            body.append(overflow_var_assign)

            # Add variable for whether we need to set old_self to current self
            # In the beginning, it is True as the first public state needs to
            # be checked against itself
            if is_init:
                ctx.new_local_vars.append(helpers.first_public_state_var(self.viper_ast))
                fps = helpers.first_public_state_var(self.viper_ast, pos).localVar()
                var_assign = self.viper_ast.LocalVarAssign(fps, self.viper_ast.TrueLit())
                body.append(var_assign)

            # Revert if a @nonreentrant lock is set
            body.extend(self._assert_unlocked(function, ctx))
            # Set all @nonreentrant locks
            body.extend(self._set_locked(function, True, ctx))

            # In the initializer initialize all fields to their default values
            if is_init:
                body.extend(self.state_translator.initialize_state(ctx.current_state, ctx))
                # Havoc self.balance, because we are not allwed to assume self.balance == 0
                # in the beginning
                body.extend(self._havoc_balance(ctx))

            msg_value = helpers.msg_value(self.viper_ast, ctx)
            if not function.is_payable():
                # If the function is not payable we assume that msg.value == 0
                # Technically speaking it is possible to send ether to a non-payable function
                # which leads to a revert, however, we implicitly require all function calls
                # to adhere to the Vyper function call interface (i.e., that they have the
                # correct types and ether).
                zero = self.viper_ast.IntLit(0)
                is_zero = self.viper_ast.EqCmp(msg_value, zero)
                payable_info = self.to_info(["Function is not payable"])
                assume = self.viper_ast.Inhale(is_zero, info=payable_info)
                body.append(assume)
            else:
                # Increase balance by msg.value
                payable_info = self.to_info(["Fuction is payable"])
                binc = self.balance_translator.increase_balance(msg_value, ctx, info=payable_info)
                body.append(binc)

                # Increase received for msg.sender by msg.value
                rec_inc = self.balance_translator.increase_received(msg_value, ctx)
                body.append(rec_inc)

                # Allocate the received ether to the sender
                if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
                    allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx)
                    resource = self.resource_translator.resource(names.WEI, [], ctx)
                    body.extend(self.allocation_translator.allocate(allocated, resource, msg_sender, msg_value, ctx))

            # If we are in a synthesized init, we don't have a function body
            if function.node:
                body_stmts = self.statement_translator.translate_stmts(function.node.body, ctx)
                body.extend(self.seqn_with_info(body_stmts, "Function body"))

            # Unset @nonreentrant locks
            body.extend(self._set_locked(function, False, ctx))

            # If we reach this point we either jumped to it by returning or got threre directly
            # because we didn't revert (yet)
            body.append(return_label)

            # Add variable for success(if_not=out_of_gas) that tracks whether the contract ran out of gas
            out_of_gas_var = helpers.out_of_gas_var(self.viper_ast)
            ctx.new_local_vars.append(out_of_gas_var)
            # Fail, if we ran out of gas
            # If the no_gas option is set, ignore it
            if not ctx.program.config.has_option(names.CONFIG_NO_GAS):
                body.append(self.fail_if(out_of_gas_var.localVar(), [], ctx))

            # If we reach this point do not revert the state
            body.append(self.viper_ast.Goto(mangled.END_LABEL))
            # Revert the state label
            body.append(revert_label)
            # Return False
            body.append(returnBool(False))
            # Havoc the return value
            if function.type.return_type:
                result_type = self.type_translator.translate(ctx.result_var.type, ctx)
                havoc = self._havoc_var(result_type, ctx)
                body.append(self.viper_ast.LocalVarAssign(ctx.result_var.local_var(ctx), havoc))
            # Revert self and old_self to the state before the function
            copy_present = self.state_translator.copy_state(ctx.pre_state, ctx.present_state, ctx)
            copy_old = self.state_translator.copy_state(ctx.pre_state, ctx.old_state, ctx)
            body.extend(copy_present)
            body.extend(copy_old)

            # The end of a program, label where return statements jump to
            body.append(end_label)

            # Postconditions hold for single transactions, checks hold before any public state,
            # invariants across transactions.
            # Therefore, after the function execution the following steps happen:
            #   - Assert the specified postconditions of the function
            #   - Assert the checks
            #   - Havoc self.balance
            #   - Assert invariants
            #   - Check accessible
            # This is necessary because a contract may receive additional money through
            # seldestruct or mining

            # In init set old to current self, if this is the first public state
            # However, the state has to be set again after havocing the balance, therefore
            # we don't update the flag
            if is_init:
                body.append(self.state_translator.check_first_public_state(ctx, False))

            old_state = ctx.present_state if is_init else ctx.pre_state
            with ctx.state_scope(ctx.present_state, old_state):
                # Save model vars
                post_stmts, modelt = self.model_translator.save_variables(ctx)
                # Assert postconditions
                for post in function.postconditions:
                    post_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL, modelt=modelt)
                    stmts, cond = self.specification_translator.translate_postcondition(post, ctx)
                    post_assert = self.viper_ast.Assert(cond, post_pos)
                    post_stmts.extend(stmts)
                    post_stmts.append(post_assert)

                for post in chain(ctx.program.general_postconditions, ctx.program.transitive_postconditions):
                    post_pos = self.to_position(post, ctx)
                    stmts, cond = self.specification_translator.translate_postcondition(post, ctx)
                    post_stmts.extend(stmts)
                    if is_init:
                        init_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL, modelt=modelt)
                        # General postconditions only have to hold for init if it succeeds
                        cond = self.viper_ast.Implies(success_var, cond, post_pos)
                        post_stmts.append(self.viper_ast.Assert(cond, init_pos))
                    else:
                        via = [Via('general postcondition', post_pos)]
                        func_pos = self.to_position(function.node, ctx, rules.POSTCONDITION_FAIL, via, modelt)
                        post_stmts.append(self.viper_ast.Assert(cond, func_pos))

                # The postconditions of the interface the contract is supposed to implement
                for itype in ctx.program.implements:
                    interface = ctx.program.interfaces[itype.name]
                    ifunc = interface.functions.get(function.name)
                    if ifunc:
                        postconditions = chain(ifunc.postconditions, interface.general_postconditions)
                    else:
                        postconditions = interface.general_postconditions

                    for post in postconditions:
                        post_pos = self.to_position(function.node or post, ctx)
                        with ctx.program_scope(interface):
                            stmts, cond = self.specification_translator.translate_postcondition(post, ctx)
                            if is_init:
                                cond = self.viper_ast.Implies(success_var, cond, post_pos)
                        apos = self.to_position(function.node or post, ctx, rules.INTERFACE_POSTCONDITION_FAIL, modelt=modelt)
                        post_assert = self.viper_ast.Assert(cond, apos)
                        post_stmts.extend(stmts)
                        post_stmts.append(post_assert)

                body.extend(self.seqn_with_info(post_stmts, "Assert postconditions"))

            # Assert checks
            # For the checks we need to differentiate between success and failure because we
            # on failure the assertion is evaluated in the old heap where events where not
            # inhaled yet
            checks_succ = []
            checks_fail = []
            for check in function.checks:
                check_pos = self.to_position(check, ctx, rules.CHECK_FAIL, modelt=modelt)
                succ_stmts, cond_succ = self.specification_translator.translate_check(check, ctx, False)
                checks_succ.extend(succ_stmts)
                checks_succ.append(self.viper_ast.Assert(cond_succ, check_pos))
                fail_stmts, cond_fail = self.specification_translator.translate_check(check, ctx, True)
                # Checks do not have to hold if init fails
                if not is_init:
                    checks_fail.extend(fail_stmts)
                    checks_fail.append(self.viper_ast.Assert(cond_fail, check_pos))

            for check in ctx.program.general_checks:
                succ_stmts, cond_succ = self.specification_translator.translate_check(check, ctx, False)
                fail_stmts, cond_fail = self.specification_translator.translate_check(check, ctx, True)

                # If we are in the initializer we might have a synthesized __init__, therefore
                # just use always check as position, else use function as position and create
                # via to always check
                if is_init:
                    check_pos = self.to_position(check, ctx, rules.CHECK_FAIL, modelt=modelt)
                else:
                    check_pos = self.to_position(check, ctx)
                    via = [Via('check', check_pos)]
                    check_pos = self.to_position(function.node, ctx, rules.CHECK_FAIL, via, modelt)

                checks_succ.extend(succ_stmts)
                checks_succ.append(self.viper_ast.Assert(cond_succ, check_pos))
                # Checks do not have to hold if __init__ fails
                if not is_init:
                    checks_fail.extend(fail_stmts)
                    checks_fail.append(self.viper_ast.Assert(cond_fail, check_pos))

            check_info = self.to_info(["Assert checks"])
            if_stmt = self.viper_ast.If(success_var, checks_succ, checks_fail, info=check_info)
            body.append(if_stmt)

            # Havoc self.balance
            body.extend(self._havoc_balance(ctx))
            # Havoc other contract state
            body.extend(self.state_translator.havoc_state_except_self(ctx.current_state, ctx))

            # In init set old to current self, if this is the first public state
            if is_init:
                body.append(self.state_translator.check_first_public_state(ctx, False))

            # Assert the invariants
            invariant_stmts, imodelt = self.model_translator.save_variables(ctx, pos)
            for inv in ctx.program.invariants:
                inv_pos = self.to_position(inv, ctx)
                # We ignore accessible here because we use a separate check
                stmts, cond = self.specification_translator.translate_invariant(inv, ctx, True)

                # If we have a synthesized __init__ we only create an
                # error message on the invariant
                if is_init:
                    # Invariants do not have to hold if __init__ fails
                    cond = self.viper_ast.Implies(success_var, cond, inv_pos)
                    apos = self.to_position(inv, ctx, rules.INVARIANT_FAIL, modelt=imodelt)
                else:
                    via = [Via('invariant', inv_pos)]
                    apos = self.to_position(function.node, ctx, rules.INVARIANT_FAIL, via, imodelt)

                invariant_stmts.extend(stmts)
                invariant_stmts.append(self.viper_ast.Assert(cond, apos))

            body.extend(self.seqn_with_info(invariant_stmts, "Assert Invariants"))

            # We check that the invariant tracks all allocation by doing a leak check.
            if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
                body.extend(self.allocation_translator.function_leak_check(ctx, pos))

            # We check accessibility by inhaling a predicate in the corresponding function
            # and checking in the end that if it has been inhaled (i.e. if we want to prove
            # that some amount is a accessible) the amount has been sent to msg.sender
            # forall a: wei_value :: perm(accessible(tag, msg.sender, a, <args>)) > 0 ==>
            #   success(if_not=out_of_gas or sender_failed) and
            #   success() ==> sent(msg.sender) - old(sent(msg.sender)) >= a
            # The tag is used to differentiate between the different invariants the accessible
            # expressions occur in
            accessibles = []
            for tag in function.analysis.accessible_tags:
                # It shouldn't be possible to write accessible for __init__
                assert function.node

                tag_inv = ctx.program.analysis.inv_tags[tag]
                inv_pos = self.to_position(tag_inv, ctx)
                vias = [Via('invariant', inv_pos)]
                acc_pos = self.to_position(function.node, ctx, rules.INVARIANT_FAIL, vias, imodelt)

                wei_value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
                amount_var = self.viper_ast.LocalVarDecl('$a', wei_value_type, inv_pos)
                acc_name = mangled.accessible_name(function.name)
                tag_lit = self.viper_ast.IntLit(tag, inv_pos)
                msg_sender = helpers.msg_sender(self.viper_ast, ctx, inv_pos)
                amount_local = self.viper_ast.LocalVar('$a', wei_value_type, inv_pos)

                arg_vars = [arg.local_var(ctx, inv_pos) for arg in args.values()]
                acc_args = [tag_lit, msg_sender, amount_local, *arg_vars]
                acc_pred = self.viper_ast.PredicateAccess(acc_args, acc_name, inv_pos)
                acc_perm = self.viper_ast.CurrentPerm(acc_pred, inv_pos)
                pos_perm = self.viper_ast.GtCmp(acc_perm, self.viper_ast.NoPerm(inv_pos), inv_pos)

                sender_failed = helpers.check_call_failed(self.viper_ast, msg_sender, inv_pos)
                out_of_gas = helpers.out_of_gas_var(self.viper_ast, inv_pos).localVar()
                not_sender_failed = self.viper_ast.Not(self.viper_ast.Or(sender_failed, out_of_gas, inv_pos), inv_pos)
                succ_if_not = self.viper_ast.Implies(not_sender_failed, success_var, inv_pos)

                sent_to = self.balance_translator.get_sent(self_var, msg_sender, ctx, inv_pos)
                pre_sent_to = self.balance_translator.get_sent(pre_self_var, msg_sender, ctx, inv_pos)

                diff = self.viper_ast.Sub(sent_to, pre_sent_to, inv_pos)
                geqa = self.viper_ast.GeCmp(diff, amount_local, inv_pos)
                succ_impl = self.viper_ast.Implies(success_var, geqa, inv_pos)
                conj = self.viper_ast.And(succ_if_not, succ_impl, inv_pos)
                impl = self.viper_ast.Implies(pos_perm, conj, inv_pos)
                trigger = self.viper_ast.Trigger([acc_pred], inv_pos)
                forall = self.viper_ast.Forall([amount_var], [trigger], impl, inv_pos)
                accessibles.append(self.viper_ast.Assert(forall, acc_pos))

            body.extend(self.seqn_with_info(accessibles, "Assert accessibles"))

            args_list = [arg.var_decl(ctx) for arg in args.values()]
            locals_list = [local.var_decl(ctx) for local in chain(locals.values(), state)]
            locals_list = [*locals_list, *ctx.new_local_vars]
            ret_list = [ret.var_decl(ctx) for ret in rets]

            viper_name = mangled.method_name(function.name)
            method = self.viper_ast.Method(viper_name, args_list, ret_list, [], [], locals_list, body, pos)
            return method

    def inline(self, call: ast.ReceiverCall, args: List[Expr], ctx: Context) -> StmtsAndExpr:
        function = ctx.program.functions[call.name]
        cpos = self.to_position(call, ctx)
        via = Via('inline', cpos)
        with ctx.inline_scope(via):
            assert function.node
            # Only private self-calls are allowed in Vyper
            assert function.is_private()

            pos = self.to_position(function.node, ctx)
            body = []

            # We keep the msg variable the same, as only msg.gas is allowed in the body of a private function.
            # In specifications we assume inline semantics, i.e., msg.sender and msg.value in the inlined function
            # correspond to msg.sender and msg.value in the caller function.

            # Add arguments to local vars, assign passed args or default argument
            for (name, var), arg in zip_longest(function.args.items(), args):
                apos = self.to_position(var.node, ctx)
                translated_arg = self._translate_var(var, ctx)
                ctx.args[name] = translated_arg
                ctx.new_local_vars.append(translated_arg.var_decl(ctx, pos))
                if not arg:
                    default_stmts, arg = self.expression_translator.translate(function.defaults[name], ctx)
                    body.extend(default_stmts)
                body.append(self.viper_ast.LocalVarAssign(translated_arg.local_var(ctx), arg, apos))

            # Define return var
            if function.type.return_type:
                ret_name = ctx.inline_prefix + mangled.RESULT_VAR
                ctx.result_var = TranslatedVar(names.RESULT, ret_name, function.type.return_type, self.viper_ast, pos)
                ctx.new_local_vars.append(ctx.result_var.var_decl(ctx, pos))
                ret_var = ctx.result_var.local_var(ctx, pos)
            else:
                ret_var = None

            # Define return label for inlined return statements
            return_label_name = ctx.inline_prefix + mangled.RETURN_LABEL
            return_label = self.viper_ast.Label(return_label_name)
            ctx.return_label = return_label_name

            # Revert if a @nonreentrant lock is set
            body.extend(self._assert_unlocked(function, ctx))
            # Set @nonreentrant locks
            body.extend(self._set_locked(function, True, ctx))

            # Translate body
            body_stmts = self.statement_translator.translate_stmts(function.node.body, ctx)
            body.extend(body_stmts)

            # Unset @nonreentrant locks
            body.extend(self._set_locked(function, False, ctx))

            seqn = self.seqn_with_info(body, f"Inlined call of {function.name}")
            return seqn + [return_label], ret_var

    def _translate_var(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        name = mangled.local_var_name(ctx.inline_prefix, var.name)
        return TranslatedVar(var.name, name, var.type, self.viper_ast, pos)

    def _assume_non_negative(self, var, ctx: Context) -> Stmt:
        zero = self.viper_ast.IntLit(0)
        gez = self.viper_ast.GeCmp(var, zero)
        return self.viper_ast.Inhale(gez)

    def _havoc_var(self, type, ctx: Context):
        havoc_name = ctx.new_local_var_name('havoc')
        havoc = self.viper_ast.LocalVarDecl(havoc_name, type)
        ctx.new_local_vars.append(havoc)
        return havoc.localVar()

    def _havoc_balance(self, ctx: Context):
        balance_type = ctx.field_types[names.ADDRESS_BALANCE]
        havoc = self._havoc_var(balance_type, ctx)
        assume_pos = self._assume_non_negative(havoc, ctx)
        inc = self.balance_translator.increase_balance(havoc, ctx)
        return [assume_pos, inc]

    def _assert_unlocked(self, function: VyperFunction, ctx: Context) -> List[Stmt]:
        keys = function.nonreentrant_keys()
        locked = [helpers.get_lock(self.viper_ast, key, ctx) for key in keys]
        if locked:
            cond = reduce(self.viper_ast.Or, locked)
            return [self.fail_if(cond, [], ctx)]
        else:
            return []

    def _set_locked(self, function: VyperFunction, value: bool, ctx: Context) -> List[Stmt]:
        keys = function.nonreentrant_keys()
        self_var = ctx.self_var.local_var(ctx)
        set_lock = lambda key: helpers.set_lock(self.viper_ast, key, value, ctx)
        return [self.viper_ast.LocalVarAssign(self_var, set_lock(key)) for key in keys]
