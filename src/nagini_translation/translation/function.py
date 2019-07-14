"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from nagini_translation.ast import names
from nagini_translation.ast.nodes import VyperFunction, VyperVar

from nagini_translation.translation.abstract import PositionTranslator, CommonTranslator
from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.statement import StatementTranslator
from nagini_translation.translation.specification import SpecificationTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.context import Context
from nagini_translation.translation.context import function_scope, inline_scope

from nagini_translation.translation import builtins

from nagini_translation.viper.ast import ViperAST
from nagini_translation.viper.typedefs import Method, StmtsAndExpr, Stmt, Expr

from nagini_translation.verification import rules


class FunctionTranslator(PositionTranslator, CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.statement_translator = StatementTranslator(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def translate(self, function: VyperFunction, ctx: Context) -> Method:
        with function_scope(ctx):
            pos = self.to_position(function.node, ctx)

            ctx.function = function
            is_init = (function.name == names.INIT)

            args = {name: self._translate_var(var, ctx) for name, var in function.args.items()}
            locals = {name: self._translate_var(var, ctx) for name, var in function.local_vars.items()}
            locals[builtins.SELF] = builtins.self_var(self.viper_ast, ctx.self_type)
            # The last publicly visible state of self
            locals[builtins.OLD_SELF] = builtins.old_self_var(self.viper_ast, ctx.self_type)
            # The state of self before the function call
            locals[builtins.PRE_SELF] = builtins.pre_self_var(self.viper_ast, ctx.self_type)
            args[builtins.MSG] = builtins.msg_var(self.viper_ast)
            args[builtins.BLOCK] = builtins.block_var(self.viper_ast)
            ctx.args = args.copy()
            ctx.locals = locals.copy()
            ctx.all_vars = {**args, **locals}

            self_var = ctx.self_var.localVar()
            old_self_var = ctx.old_self_var.localVar()
            pre_self_var = locals[builtins.PRE_SELF].localVar()

            success_var = builtins.success_var(self.viper_ast)
            ctx.success_var = success_var
            revert_label = builtins.revert_label(self.viper_ast)
            ctx.revert_label = builtins.REVERT_LABEL

            rets = [success_var]
            end_label = builtins.end_label(self.viper_ast)
            ctx.end_label = builtins.END_LABEL

            if function.type.return_type:
                ret_type = self.type_translator.translate(function.type.return_type, ctx)
                ret_var = builtins.ret_var(self.viper_ast, ret_type, pos)
                rets.append(ret_var)
                ctx.result_var = ret_var

            pres = ctx.immutable_permissions

            body = []

            # Assume all unchecked invariants
            unchecked_invs = [self.viper_ast.Inhale(inv) for inv in ctx.unchecked_invariants]
            body.extend(self._seqn_with_info(unchecked_invs, "Assume all unchecked invariants"))

            argument_conds = []
            for var in function.args.values():
                local_var = args[var.name].localVar()
                assumptions = self.type_translator.type_assumptions(local_var, var.type, ctx)
                argument_conds.extend(assumptions)

            argument_cond_assumes = [self.viper_ast.Inhale(c) for c in argument_conds]
            ui_info_msg = "Assume non-negativeness of uint256 and sizes of array args"
            body.extend(self._seqn_with_info(argument_cond_assumes, ui_info_msg))

            # Assume user-specified invariants
            translate_inv = self.specification_translator.translate_invariant
            inv_pres = []
            for inv in ctx.program.invariants:
                expr = translate_inv(inv, ctx, True, is_init)
                if expr:
                    ppos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                    inv_pres.append(self.viper_ast.Inhale(expr, ppos))

            iv_info_msg = "Assume invariants"
            body.extend(self._seqn_with_info(inv_pres, iv_info_msg))

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

            msg_value = builtins.msg_value_field(self.viper_ast)
            value_acc = self.viper_ast.FieldAccess(ctx.msg_var.localVar(), msg_value)
            # If a function is not payable and money is sent, revert
            if not function.is_payable():
                zero = self.viper_ast.IntLit(0)
                # TODO: how to handle this case?
                # is_not_zero = self.viper_ast.NeCmp(value_acc, zero)
                # body.append(self.fail_if(is_not_zero, ctx))
                is_zero = self.viper_ast.EqCmp(value_acc, zero)
                payable_info = self.to_info(["Function is not payable"])
                assume = self.viper_ast.Inhale(is_zero, info=payable_info)
                body.append(assume)
            else:
                # Increase balance by msg.value
                balance_type = ctx.field_types[names.SELF_BALANCE]
                get_balance = builtins.struct_get(self.viper_ast, self_var, names.SELF_BALANCE, balance_type, ctx.self_type)
                inc_sum = self.viper_ast.Add(get_balance, value_acc)
                payable_info = self.to_info(["Fuction is payable"])
                inc = builtins.struct_set(self.viper_ast, self_var, inc_sum, names.SELF_BALANCE, ctx.self_type)
                self_assign = self.viper_ast.LocalVarAssign(self_var, inc, info=payable_info)
                body.append(self_assign)

                # Increase received for msg.sender by msg.value
                msg_sender = builtins.msg_sender_field_acc(self.viper_ast)
                rec_type = ctx.field_types[builtins.RECEIVED_FIELD]
                rec = builtins.struct_get(self.viper_ast, self_var, builtins.RECEIVED_FIELD, rec_type, ctx.self_type)
                # TODO: improve this type stuff
                rec_sender = builtins.map_get(self.viper_ast, rec, msg_sender, self.viper_ast.Int, self.viper_ast.Int)
                rec_inc_sum = self.viper_ast.Add(rec_sender, value_acc)
                # TODO: improve this type stuff
                rec_set = builtins.map_set(self.viper_ast, rec, msg_sender, rec_inc_sum, self.viper_ast.Int, self.viper_ast.Int)
                self_set = builtins.struct_set(self.viper_ast, self_var, rec_set, builtins.RECEIVED_FIELD, ctx.self_type)
                body.append(self.viper_ast.LocalVarAssign(self_var, self_set))

            body_stmts = self.statement_translator.translate_stmts(function.node.body, ctx)
            body.extend(self._seqn_with_info(body_stmts, "Function body"))

            # # Fail, if we ran out of gas
            # out_of_gas_var = builtins.out_of_gas_var(self.viper_ast)
            # ctx.new_local_vars.append(out_of_gas_var)
            # body.append(self.fail_if(out_of_gas_var.localVar(), ctx))

            # Add variable for success(-msg.sender) that tracks whether a call to
            # msg.sender failed
            ctx.new_local_vars.append(builtins.msg_sender_call_fail_var(self.viper_ast))

            # If we reach this point do not revert the state
            body.append(self.viper_ast.Goto(ctx.end_label))
            # Revert the state
            body.append(revert_label)
            # Return False
            body.append(returnBool(False))
            # Revert self and old_self to the state before the function
            # The return value does not have to be havoced because it was never assigned to
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
                    via = [('general postcondition', post_pos)]
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
                    via = [('check', check_pos)]
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
                    via = [('invariant', inv_pos)]
                    apos = self.to_position(function.node, ctx, rules.INVARIANT_FAIL, via)

                invariant_stmts.append(self.viper_ast.Assert(cond, apos))

            body.extend(self._seqn_with_info(invariant_stmts, "Assert Invariants"))

            args_list = list(args.values())
            locals_list = [*locals.values(), *ctx.new_local_vars]

            viper_name = builtins.method_name(function.name)
            method = self.viper_ast.Method(viper_name, args_list, rets, pres, [], locals_list, body, pos)
            return method

    def inline(self, function: VyperFunction, args: List[Expr], ctx: Context) -> StmtsAndExpr:
        with inline_scope(ctx):
            pos = self.to_position(function.node, ctx)
            body = []

            # Define new msg variable
            msg_name = ctx.inline_prefix + builtins.MSG
            msg_decl = self.viper_ast.LocalVarDecl(msg_name, self.viper_ast.Ref)
            ctx.all_vars[names.MSG] = msg_decl
            ctx.new_local_vars.append(msg_decl)

            # Add permissions for msg.sender and msg.value
            msg_sender_field = builtins.msg_sender_field(self.viper_ast)
            msg_sender = self.viper_ast.FieldAccess(msg_decl.localVar(), msg_sender_field)
            msg_sender_perm = self._create_field_access_predicate(msg_sender, 0, ctx)
            body.append(self.viper_ast.Inhale(msg_sender_perm))

            # msg.sender == self
            self_address = builtins.self_address(self.viper_ast)
            msg_sender_eq = self.viper_ast.EqCmp(msg_sender, self_address)
            body.append(self.viper_ast.Inhale(msg_sender_eq))

            # Add permissions for msg.value
            msg_value_field = builtins.msg_value_field(self.viper_ast)
            msg_value = self.viper_ast.FieldAccess(msg_decl.localVar(), msg_value_field)
            msg_value_perm = self._create_field_access_predicate(msg_value, 0, ctx)
            body.append(self.viper_ast.Inhale(msg_value_perm))

            # msg.value == 0
            # TODO: Support sending money
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
                ret_name = ctx.inline_prefix + builtins.RESULT_VAR
                ret_var_decl = self.viper_ast.LocalVarDecl(ret_name, ret_type, pos)
                ctx.new_local_vars.append(ret_var_decl)
                ctx.result_var = ret_var_decl
                ret_var = ret_var_decl.localVar()
            else:
                ret_var = None

            # Define end label for inlined return statements
            end_label_name = ctx.inline_prefix + builtins.END_LABEL
            end_label = self.viper_ast.Label(end_label_name)
            ctx.end_label = end_label_name

            # Translate body
            body_stmts = self.statement_translator.translate_stmts(function.node.body, ctx)
            body.extend(body_stmts)

            seqn = self._seqn_with_info(body, f"Inlined call of {function.name}")
            return seqn + [end_label], ret_var

    def _translate_var(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        type = self.type_translator.translate(var.type, ctx)
        name = ctx.inline_prefix + builtins.local_var_name(var.name)
        return self.viper_ast.LocalVarDecl(name, type, pos)

    def _non_negative(self, var, ctx: Context) -> Stmt:
        zero = self.viper_ast.IntLit(0)
        return self.viper_ast.GeCmp(var, zero)

    def _assume_non_negative(self, var, ctx: Context) -> Stmt:
        gez = self._non_negative(var, ctx)
        return self.viper_ast.Inhale(gez)

    def _havoc_balance(self, ctx: Context):
        self_var = ctx.self_var.localVar()

        havoc_name = ctx.new_local_var_name('havoc')
        havoc = self.viper_ast.LocalVarDecl(havoc_name, self.viper_ast.Int)
        ctx.new_local_vars.append(havoc)
        assume_pos = self._assume_non_negative(havoc.localVar(), ctx)

        balance_type = ctx.field_types[names.SELF_BALANCE]
        get_balance = builtins.struct_get(self.viper_ast, self_var, names.SELF_BALANCE, balance_type, ctx.self_type)
        inc_sum = self.viper_ast.Add(get_balance, havoc.localVar())
        inc = builtins.struct_set(self.viper_ast, self_var, inc_sum, names.SELF_BALANCE, ctx.self_type)
        self_assign = self.viper_ast.LocalVarAssign(self_var, inc)

        return [assume_pos, self_assign]

    def _create_field_access_predicate(self, field_access, amount, ctx: Context):
        if amount == 1:
            perm = self.viper_ast.FullPerm()
        else:
            perm = builtins.read_perm(self.viper_ast)
        return self.viper_ast.FieldAccessPredicate(field_access, perm)
