"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from itertools import chain
from typing import List

from twovyper.ast import names
from twovyper.ast import types
from twovyper.ast.nodes import VyperFunction, VyperVar

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Method, StmtsAndExpr, Stmt, Expr

from twovyper.translation.abstract import PositionTranslator, CommonTranslator
from twovyper.translation.expression import ExpressionTranslator
from twovyper.translation.statement import StatementTranslator
from twovyper.translation.specification import SpecificationTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.balance import BalanceTranslator
from twovyper.translation.context import (
    Context, function_scope, inline_scope, self_scope
)

from twovyper.translation import mangled
from twovyper.translation import helpers

from twovyper.verification import rules
from twovyper.verification.error import Via


class FunctionTranslator(PositionTranslator, CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.statement_translator = StatementTranslator(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)
        self.balance_translator = BalanceTranslator(viper_ast)

    def translate(self, function: VyperFunction, ctx: Context) -> Method:
        with function_scope(ctx):
            # A synthesized __init__ does not have a position in the file
            if function.node:
                pos = self.to_position(function.node, ctx)
            else:
                pos = self.no_position()

            ctx.function = function
            is_init = (function.name == names.INIT)

            args = {name: self._translate_var(var, ctx) for name, var in function.args.items()}
            locals = {name: self._translate_var(var, ctx) for name, var in function.local_vars.items()}
            locals[names.SELF] = helpers.self_var(self.viper_ast, ctx.self_type)
            # The last publicly visible state of self
            locals[mangled.OLD_SELF] = helpers.old_self_var(self.viper_ast, ctx.self_type)
            # The state of self before the function call
            locals[mangled.PRE_SELF] = helpers.pre_self_var(self.viper_ast, ctx.self_type)
            # The state of self when the transaction was issued
            locals[mangled.ISSUED_SELF] = helpers.issued_self_var(self.viper_ast, ctx.self_type)
            # The block variable
            block_type = self.type_translator.translate(types.BLOCK_TYPE, ctx)
            locals[names.BLOCK] = self.viper_ast.LocalVarDecl(mangled.BLOCK, block_type)
            # The msg variable
            msg_type = self.type_translator.translate(types.MSG_TYPE, ctx)
            locals[names.MSG] = self.viper_ast.LocalVarDecl(mangled.MSG, msg_type)
            # The tx variable
            tx_type = self.type_translator.translate(types.TX_TYPE, ctx)
            locals[names.TX] = self.viper_ast.LocalVarDecl(mangled.TX, tx_type)
            # We create copies of args and locals because ctx is allowed to modify them
            ctx.args = args.copy()
            ctx.locals = locals.copy()
            ctx.all_vars = {**args, **locals}

            self_var = ctx.self_var.localVar()
            old_self_var = ctx.old_self_var.localVar()
            pre_self_var = ctx.pre_self_var.localVar()
            issued_self_var = ctx.issued_self_var.localVar()

            ctx.success_var = helpers.success_var(self.viper_ast)
            rets = [ctx.success_var]
            success_var = ctx.success_var.localVar()

            end_label = self.viper_ast.Label(mangled.END_LABEL)
            return_label = self.viper_ast.Label(mangled.RETURN_LABEL)
            revert_label = self.viper_ast.Label(mangled.REVERT_LABEL)

            ctx.return_label = mangled.RETURN_LABEL
            ctx.revert_label = mangled.REVERT_LABEL

            if function.type.return_type:
                ret_type = self.type_translator.translate(function.type.return_type, ctx)
                ret_var = helpers.ret_var(self.viper_ast, ret_type, pos)
                rets.append(ret_var)
                ctx.result_var = ret_var

            body = []

            # Assume type assumptions for self state
            self_ass = self.type_translator.type_assumptions(self_var, ctx.self_type, ctx)
            self_assumptions = [self.viper_ast.Inhale(inv) for inv in self_ass]
            body.extend(self._seqn_with_info(self_assumptions, "Self state assumptions"))

            # Assume type assumptions for issued self state
            if function.analysis.uses_issued:
                issued = self.type_translator.type_assumptions(issued_self_var, ctx.self_type, ctx)
                issued_assumptions = [self.viper_ast.Inhale(a) for a in issued]
                body.extend(self._seqn_with_info(issued_assumptions, "Issued state assumptions"))

            # Assume type assumptions for arguments
            argument_conds = []
            for var in function.args.values():
                local_var = args[var.name].localVar()
                assumptions = self.type_translator.type_assumptions(local_var, var.type, ctx)
                argument_conds.extend(assumptions)

            argument_cond_assumes = [self.viper_ast.Inhale(c) for c in argument_conds]
            ui_info_msg = "Assume type assumptions for arguments"
            body.extend(self._seqn_with_info(argument_cond_assumes, ui_info_msg))

            # Assume type assumptions for block
            block_var = ctx.block_var.localVar()
            block_conds = self.type_translator.type_assumptions(block_var, types.BLOCK_TYPE, ctx)
            block_assumes = [self.viper_ast.Inhale(c) for c in block_conds]
            block_info_msg = "Assume type assumptions for block"
            body.extend(self._seqn_with_info(block_assumes, block_info_msg))

            # Assume type assumptions for msg
            msg_var = ctx.msg_var.localVar()
            msg_conds = self.type_translator.type_assumptions(msg_var, types.MSG_TYPE, ctx)
            # We additionally know that msg.sender != 0
            zero = self.viper_ast.IntLit(0)
            msg_sender = helpers.msg_sender(self.viper_ast, ctx)
            neq0 = self.viper_ast.NeCmp(msg_sender, zero)
            msg_assumes = [self.viper_ast.Inhale(c) for c in chain(msg_conds, [neq0])]
            msg_info_msg = "Assume type assumptions for msg"
            body.extend(self._seqn_with_info(msg_assumes, msg_info_msg))

            # Assume unchecked and user-specified invariants
            inv_pres_issued = []
            inv_pres_self = []

            # Translate the invariants for the issued state. Since we don't know anything about
            # the state before then, we use the issued state itself as the old state
            if not is_init and function.analysis.uses_issued:
                with self_scope(ctx.issued_self_var, ctx.issued_self_var, ctx):
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
                last_state = ctx.issued_self_var if function.analysis.uses_issued else ctx.self_var
                with self_scope(ctx.self_var, last_state, ctx):
                    for inv in ctx.unchecked_invariants():
                        inv_pres_self.append(self.viper_ast.Inhale(inv))

                    for inv in ctx.program.invariants:
                        ppos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        stmts, expr = self.specification_translator.translate_invariant(inv, ctx)
                        inv_pres_self.extend(stmts)
                        inv_pres_self.append(self.viper_ast.Inhale(expr, ppos))

            iv_info_msg = "Assume invariants for issued self"
            body.extend(self._seqn_with_info(inv_pres_issued, iv_info_msg))
            iv_info_msg = "Assume invariants for self"
            body.extend(self._seqn_with_info(inv_pres_self, iv_info_msg))

            # old_self and pre_self are the same as self in the beginning
            copy_old = self.viper_ast.LocalVarAssign(old_self_var, self_var)
            copy_pre = self.viper_ast.LocalVarAssign(pre_self_var, self_var)
            body.extend([copy_old, copy_pre])

            def returnBool(value: bool) -> Stmt:
                lit = self.viper_ast.TrueLit if value else self.viper_ast.FalseLit
                return self.viper_ast.LocalVarAssign(success_var, lit())

            # If we do not encounter an exception we will return success
            body.append(returnBool(True))

            # Add variable for whether we need to set old_self to current self
            # In the beginning, it is True as the first public state needs to
            # be checked against itself
            if is_init:
                ctx.new_local_vars.append(helpers.first_public_state_var(self.viper_ast))
                fps = helpers.first_public_state_var(self.viper_ast, pos).localVar()
                var_assign = self.viper_ast.LocalVarAssign(fps, self.viper_ast.TrueLit())
                body.append(var_assign)

            # In the initializer initialize all fields to their default values
            if is_init:
                stmts, default_self = self.type_translator.default_value(None, ctx.self_type, ctx)
                self_assign = self.viper_ast.LocalVarAssign(self_var, default_self)
                body.extend(stmts)
                body.append(self_assign)

                # Havoc self.balance, because we are not allwed to assume self.balance == 0
                # in the beginning
                body.extend(self._havoc_balance(ctx))

            msg_value = helpers.msg_value(self.viper_ast, ctx)
            # If a function is not payable and money is sent, revert
            if not function.is_payable():
                zero = self.viper_ast.IntLit(0)
                # TODO: how to handle this case?
                # is_not_zero = self.viper_ast.NeCmp(value_acc, zero)
                # body.append(self.fail_if(is_not_zero, ctx))
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

            # If we are in a synthesized init, we don't have a function body
            if function.node:
                body_stmts = self.statement_translator.translate_stmts(function.node.body, ctx)
                body.extend(self._seqn_with_info(body_stmts, "Function body"))

            # If we reach this point we either jumped to it by returning or got threre directly
            # because we didn't revert (yet)
            body.append(return_label)

            # Add variable for success(if_not=overflow) that tracks whether an overflow happened
            overflow_var = helpers.overflow_var(self.viper_ast)
            ctx.new_local_vars.append(overflow_var)

            # Add variable for success(if_not=out_of_gas) that tracks whether the contract ran out of gas
            out_of_gas_var = helpers.out_of_gas_var(self.viper_ast)
            ctx.new_local_vars.append(out_of_gas_var)
            # Fail, if we ran out of gas
            # If the no_gas option is set, ignore it
            if not ctx.program.config.has_option(names.CONFIG_NO_GAS):
                msg_sender_call_fail = helpers.msg_sender_call_fail_var(self.viper_ast).localVar()
                assume_msg_sender_call_fail = self.viper_ast.Inhale(msg_sender_call_fail)
                body.append(self.fail_if(out_of_gas_var.localVar(), [assume_msg_sender_call_fail], ctx))

            # Add variable for success(if_not=sender_failed) that tracks whether a call to
            # msg.sender failed
            ctx.new_local_vars.append(helpers.msg_sender_call_fail_var(self.viper_ast))

            # If we reach this point do not revert the state
            body.append(self.viper_ast.Goto(mangled.END_LABEL))
            # Revert the state label
            body.append(revert_label)
            # Return False
            body.append(returnBool(False))
            # Havoc the return value
            if function.type.return_type:
                havoc = self._havoc_var(ctx.result_var.typ(), ctx)
                body.append(self.viper_ast.LocalVarAssign(ctx.result_var.localVar(), havoc))
            # Revert self and old_self to the state before the function
            copy_self = self.viper_ast.LocalVarAssign(self_var, pre_self_var)
            copy_old = self.viper_ast.LocalVarAssign(old_self_var, pre_self_var)
            body.extend([copy_self, copy_old])

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
                body.append(helpers.check_first_public_state(self.viper_ast, ctx, False))

            # Assert postconditions
            post_stmts = []
            for post in function.postconditions:
                post_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL)
                stmts, cond = self.specification_translator.translate_postcondition(post, ctx, False)
                post_assert = self.viper_ast.Assert(cond, post_pos)
                post_stmts.extend(stmts)
                post_stmts.append(post_assert)

            for post in chain(ctx.program.general_postconditions, ctx.program.transitive_postconditions):
                post_pos = self.to_position(post, ctx)
                stmts, cond = self.specification_translator.translate_postcondition(post, ctx, is_init)
                post_stmts.extend(stmts)
                if is_init:
                    init_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL)
                    # General postconditions only have to hold for init if it succeeds
                    cond = self.viper_ast.Implies(success_var, cond, post_pos)
                    post_stmts.append(self.viper_ast.Assert(cond, init_pos))
                else:
                    via = [Via('general postcondition', post_pos)]
                    func_pos = self.to_position(function.node, ctx, rules.POSTCONDITION_FAIL, via)
                    post_stmts.append(self.viper_ast.Assert(cond, func_pos))

            body.extend(self._seqn_with_info(post_stmts, "Assert postconditions"))

            # Assert checks
            # For the checks we need to differentiate between success and failure because we
            # on failure the assertion is evaluated in the old heap where events where not
            # inhaled yet
            checks_succ = []
            checks_fail = []
            for check in function.checks:
                check_pos = self.to_position(check, ctx, rules.CHECK_FAIL)
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
                    check_pos = self.to_position(check, ctx, rules.CHECK_FAIL)
                else:
                    check_pos = self.to_position(check, ctx)
                    via = [Via('check', check_pos)]
                    check_pos = self.to_position(function.node, ctx, rules.CHECK_FAIL, via)

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

            # In init set old to current self, if this is the first public state
            if is_init:
                body.append(helpers.check_first_public_state(self.viper_ast, ctx, False))

            # Assert the invariants
            invariant_stmts = []
            for inv in ctx.program.invariants:
                inv_pos = self.to_position(inv, ctx)
                # We ignore accessible here because we use a separate check
                stmts, cond = self.specification_translator.translate_invariant(inv, ctx, True)

                # If we have a synthesized __init__ we only create an
                # error message on the invariant
                if is_init:
                    # Invariants do not have to hold if __init__ fails
                    cond = self.viper_ast.Implies(success_var, cond, inv_pos)
                    apos = self.to_position(inv, ctx, rules.INVARIANT_FAIL)
                else:
                    via = [Via('invariant', inv_pos)]
                    apos = self.to_position(function.node, ctx, rules.INVARIANT_FAIL, via)

                invariant_stmts.extend(stmts)
                invariant_stmts.append(self.viper_ast.Assert(cond, apos))

            body.extend(self._seqn_with_info(invariant_stmts, "Assert Invariants"))

            # We check accessibility by inhaling a predicate in the corresponding function
            # and checking in the end that if it has been inhaled (i.e. if we want to prove
            # that some amount is a accessible) the amount has been sent to msg.sender
            # forall a: wei_value :: perm(accessible(tag, msg.sender, a, <args>)) > 0 ==>
            #   success(if_not=sender_failed) and
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
                acc_pos = self.to_position(function.node, ctx, rules.INVARIANT_FAIL, vias)

                wei_value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
                amount_var = self.viper_ast.LocalVarDecl('$a', wei_value_type, inv_pos)
                acc_name = mangled.accessible_name(function.name)
                tag_lit = self.viper_ast.IntLit(tag, inv_pos)
                msg_sender = helpers.msg_sender(self.viper_ast, ctx, inv_pos)
                amount_local = self.viper_ast.LocalVar('$a', wei_value_type, inv_pos)

                arg_vars = [arg.localVar() for arg in args.values()]
                acc_args = [tag_lit, msg_sender, amount_local, *arg_vars]
                acc_pred = self.viper_ast.PredicateAccess(acc_args, acc_name, inv_pos)
                acc_perm = self.viper_ast.CurrentPerm(acc_pred, inv_pos)
                pos_perm = self.viper_ast.GtCmp(acc_perm, self.viper_ast.NoPerm(inv_pos), inv_pos)

                sender_failed = helpers.msg_sender_call_fail_var(self.viper_ast, inv_pos).localVar()
                not_sender_failed = self.viper_ast.Not(sender_failed, inv_pos)
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

            body.extend(self._seqn_with_info(accessibles, "Assert accessibles"))

            args_list = list(args.values())
            locals_list = [*locals.values(), *ctx.new_local_vars]

            viper_name = mangled.method_name(function.name)
            method = self.viper_ast.Method(viper_name, args_list, rets, [], [], locals_list, body, pos)
            return method

    def inline(self, call: ast.Call, args: List[Expr], ctx: Context) -> StmtsAndExpr:
        function = ctx.program.functions[call.func.attr]
        cpos = self.to_position(call, ctx)
        via = Via('inline', cpos)
        with inline_scope(via, ctx):
            assert function.node
            # Only private self-calls are allowed in Vyper
            # In specifications, we also allow pure calls
            assert function.is_private() or function.is_pure()

            pos = self.to_position(function.node, ctx)
            body = []

            # Define new msg variable
            # This is only necessary for msg.gas, as msg.sender and msg.value are not
            # allowed in private functions
            msg_type = self.type_translator.translate(types.MSG_TYPE, ctx)
            msg_name = ctx.inline_prefix + mangled.MSG
            msg_decl = self.viper_ast.LocalVarDecl(msg_name, msg_type)
            ctx.all_vars[names.MSG] = msg_decl
            ctx.locals[names.MSG] = msg_decl
            ctx.new_local_vars.append(msg_decl)

            # Add arguments to local vars, assign passed args
            for (name, var), arg in zip(function.args.items(), args):
                apos = self.to_position(var.node, ctx)
                arg_decl = self._translate_var(var, ctx)
                ctx.all_vars[name] = arg_decl
                ctx.new_local_vars.append(arg_decl)
                body.append(self.viper_ast.LocalVarAssign(arg_decl.localVar(), arg, apos))

            # Add prefixed locals to local vars
            for name, var in function.local_vars.items():
                var_decl = self._translate_var(var, ctx)
                ctx.all_vars[name] = var_decl
                ctx.new_local_vars.append(var_decl)

            # Define return var
            if function.type.return_type:
                ret_type = self.type_translator.translate(function.type.return_type, ctx)
                ret_name = ctx.inline_prefix + mangled.RESULT_VAR
                ret_var_decl = self.viper_ast.LocalVarDecl(ret_name, ret_type, pos)
                ctx.new_local_vars.append(ret_var_decl)
                ctx.result_var = ret_var_decl
                ret_var = ret_var_decl.localVar()
            else:
                ret_var = None

            # Define return label for inlined return statements
            return_label_name = ctx.inline_prefix + mangled.RETURN_LABEL
            return_label = self.viper_ast.Label(return_label_name)
            ctx.return_label = return_label_name

            # Translate body
            body_stmts = self.statement_translator.translate_stmts(function.node.body, ctx)
            body.extend(body_stmts)

            seqn = self._seqn_with_info(body, f"Inlined call of {function.name}")
            return seqn + [return_label], ret_var

    def _translate_var(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        type = self.type_translator.translate(var.type, ctx)
        name = ctx.inline_prefix + mangled.local_var_name(var.name)
        return self.viper_ast.LocalVarDecl(name, type, pos)

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
        balance_type = ctx.field_types[names.SELF_BALANCE]
        havoc = self._havoc_var(balance_type, ctx)
        assume_pos = self._assume_non_negative(havoc, ctx)
        inc = self.balance_translator.increase_balance(havoc, ctx)
        return [assume_pos, inc]
