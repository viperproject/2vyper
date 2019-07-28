"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from itertools import chain
from typing import List

from nagini_translation.ast import names
from nagini_translation.ast.nodes import VyperFunction, VyperVar
from nagini_translation.ast import types

from nagini_translation.translation.abstract import PositionTranslator, CommonTranslator
from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.statement import StatementTranslator
from nagini_translation.translation.specification import SpecificationTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.balance import BalanceTranslator
from nagini_translation.translation.context import Context
from nagini_translation.translation.context import function_scope, inline_scope

from nagini_translation.translation import mangled
from nagini_translation.translation import helpers

from nagini_translation.viper.ast import ViperAST
from nagini_translation.viper.typedefs import Method, StmtsAndExpr, Stmt, Expr

from nagini_translation.verification import rules
from nagini_translation.verification.error import Via


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
            pos = self.to_position(function.node, ctx)

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
            # We create copies of args and locals because ctx is allowed to modify them
            ctx.args = args.copy()
            ctx.locals = locals.copy()
            ctx.all_vars = {**args, **locals}

            self_var = ctx.self_var.localVar()
            old_self_var = ctx.old_self_var.localVar()
            pre_self_var = ctx.pre_self_var.localVar()
            issued_self_var = ctx.issued_self_var.localVar()

            success_var = helpers.success_var(self.viper_ast)
            ctx.success_var = success_var
            rets = [success_var]

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

            # Assume all unchecked invariants
            unchecked_invs = [self.viper_ast.Inhale(inv) for inv in ctx.unchecked_invariants]
            body.extend(self._seqn_with_info(unchecked_invs, "Self state assumptions"))

            # Assume type assumptions for issued self state
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

            # Assume user-specified invariants
            translate_inv = self.specification_translator.translate_invariant
            inv_pres_issued = []
            inv_pres_self = []

            for inv in ctx.program.invariants:
                # We translate the invariants once for the issued state alone and once for
                # the self state with the issued state as the old state
                for b in [True, False]:
                    expr = translate_inv(inv, ctx, b, is_init, True)
                    inv_pres = inv_pres_issued if b else inv_pres_self
                    if expr:
                        ppos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        inv_pres.append(self.viper_ast.Inhale(expr, ppos))

            iv_info_msg = "Assume invariants for issued self"
            body.extend(self._seqn_with_info(inv_pres_issued, iv_info_msg))
            iv_info_msg = "Assume invariants for self"
            body.extend(self._seqn_with_info(inv_pres_self, iv_info_msg))

            # old_self and pre_self are the same as self in the beginning
            copy_old = self.viper_ast.LocalVarAssign(old_self_var, self_var)
            copy_pre = self.viper_ast.LocalVarAssign(pre_self_var, self_var)
            body.extend([copy_old, copy_pre])

            def returnBool(value: bool) -> Stmt:
                local_var = success_var.localVar()
                lit = self.viper_ast.TrueLit if value else self.viper_ast.FalseLit
                return self.viper_ast.LocalVarAssign(local_var, lit())

            # If we do not encounter an exception we will return success
            body.append(returnBool(True))

            # In the initializer initialize all fields to their default values
            if function.name == names.INIT:
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

            body_stmts = self.statement_translator.translate_stmts(function.node.body, ctx)
            body.extend(self._seqn_with_info(body_stmts, "Function body"))

            # If we reach this point we either jumped to it by returning or got threre directly
            # because we didn't revert (yet)
            body.append(return_label)

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
                body.append(self.viper_ast.LocalVarAssign(ctx.result_var.localVar(), havoc.localVar()))
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
            # This is necessary because a contract may receive additional money through
            # seldestruct or mining

            # Assert postconditions
            post_stmts = []
            for post in function.postconditions:
                post_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL)
                cond = self.specification_translator.translate_postcondition(post, ctx, False)
                post_assert = self.viper_ast.Assert(cond, post_pos)
                post_stmts.append(post_assert)

            for post in ctx.program.general_postconditions:
                post_pos = self.to_position(post, ctx)
                cond = self.specification_translator.translate_postcondition(post, ctx, is_init)
                if is_init:
                    init_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL)
                    # General postconditions only have to hold for init if it succeeds
                    cond = self.viper_ast.Implies(success_var.localVar(), cond, post_pos)
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
                cond_succ = self.specification_translator.translate_check(check, ctx, is_fail=False)
                checks_succ.append(self.viper_ast.Assert(cond_succ, check_pos))
                cond_fail = self.specification_translator.translate_check(check, ctx, is_fail=True)
                # Checks do not have to hold if init fails
                if not is_init:
                    checks_fail.append(self.viper_ast.Assert(cond_fail, check_pos))

            for check in ctx.program.general_checks:
                cond_succ = self.specification_translator.translate_check(check, ctx, is_init, False)
                cond_fail = self.specification_translator.translate_check(check, ctx, is_init, True)

                # If we are in the initializer we might have a synthesized __init__, therefore
                # just use always check as position, else use function as position and create
                # via to always check
                if is_init:
                    check_pos = self.to_position(check, ctx, rules.CHECK_FAIL)
                else:
                    check_pos = self.to_position(check, ctx)
                    via = [Via('check', check_pos)]
                    check_pos = self.to_position(function.node, ctx, rules.CHECK_FAIL, via)

                checks_succ.append(self.viper_ast.Assert(cond_succ, check_pos))
                # Checks do not have to hold if __init__ fails
                if not is_init:
                    checks_fail.append(self.viper_ast.Assert(cond_fail, check_pos))

            check_info = self.to_info(["Assert checks"])
            if_stmt = self.viper_ast.If(success_var.localVar(), checks_succ, checks_fail, info=check_info)
            body.append(if_stmt)

            # Havoc self.balance
            body.extend(self._havoc_balance(ctx))

            # Assert the invariants
            invariant_stmts = []
            translate_inv = self.specification_translator.translate_invariant
            for inv in ctx.program.invariants:
                inv_pos = self.to_position(inv, ctx)
                cond = translate_inv(inv, ctx, False, is_init)

                # If we have a synthesized __init__ we only create an
                # error message on the invariant
                if is_init:
                    # Invariants do not have to hold if __init__ fails
                    cond = self.viper_ast.Implies(success_var.localVar(), cond, inv_pos)
                    apos = self.to_position(inv, ctx, rules.INVARIANT_FAIL)
                else:
                    via = [Via('invariant', inv_pos)]
                    apos = self.to_position(function.node, ctx, rules.INVARIANT_FAIL, via)

                invariant_stmts.append(self.viper_ast.Assert(cond, apos))

            body.extend(self._seqn_with_info(invariant_stmts, "Assert Invariants"))

            args_list = list(args.values())
            locals_list = [*locals.values(), *ctx.new_local_vars]

            viper_name = mangled.method_name(function.name)
            method = self.viper_ast.Method(viper_name, args_list, rets, [], [], locals_list, body, pos)
            return method

    def inline(self, function: VyperFunction, args: List[Expr], ctx: Context) -> StmtsAndExpr:
        with inline_scope(ctx):
            pos = self.to_position(function.node, ctx)
            body = []

            # Define new msg variable
            msg_type = self.type_translator.translate(types.MSG_TYPE, ctx)
            msg_name = ctx.inline_prefix + mangled.MSG
            msg_decl = self.viper_ast.LocalVarDecl(msg_name, msg_type)
            ctx.all_vars[names.MSG] = msg_decl
            ctx.locals[names.MSG] = msg_decl
            ctx.new_local_vars.append(msg_decl)

            # msg.sender == self
            msg_sender = helpers.msg_sender(self.viper_ast, ctx)
            self_address = helpers.self_address(self.viper_ast)
            msg_sender_eq = self.viper_ast.EqCmp(msg_sender, self_address)
            body.append(self.viper_ast.Inhale(msg_sender_eq))

            # msg.value == 0
            # TODO: Support sending money
            msg_value = helpers.msg_value(self.viper_ast, ctx)
            msg_value_eq = self.viper_ast.EqCmp(msg_value, self.viper_ast.IntLit(0))
            body.append(self.viper_ast.Inhale(msg_value_eq))

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

    def _non_negative(self, var, ctx: Context) -> Stmt:
        zero = self.viper_ast.IntLit(0)
        return self.viper_ast.GeCmp(var, zero)

    def _assume_non_negative(self, var, ctx: Context) -> Stmt:
        gez = self._non_negative(var, ctx)
        return self.viper_ast.Inhale(gez)

    def _havoc_var(self, type, ctx: Context):
        havoc_name = ctx.new_local_var_name('havoc')
        havoc = self.viper_ast.LocalVarDecl(havoc_name, type)
        ctx.new_local_vars.append(havoc)
        return havoc

    def _havoc_balance(self, ctx: Context):
        self_var = ctx.self_var.localVar()

        havoc = self._havoc_var(self.viper_ast.Int, ctx)
        assume_pos = self._assume_non_negative(havoc.localVar(), ctx)

        balance_type = ctx.field_types[names.SELF_BALANCE]
        get_balance = helpers.struct_get(self.viper_ast, self_var, names.SELF_BALANCE, balance_type, ctx.self_type)
        inc_sum = self.viper_ast.Add(get_balance, havoc.localVar())
        inc = helpers.struct_set(self.viper_ast, self_var, inc_sum, names.SELF_BALANCE, ctx.self_type)
        self_assign = self.viper_ast.LocalVarAssign(self_var, inc)

        return [assume_pos, self_assign]
