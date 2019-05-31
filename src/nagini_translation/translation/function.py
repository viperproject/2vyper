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
from nagini_translation.translation.context import function_scope, use_old_scope, inline_scope

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
            args[builtins.SELF] = ctx.self_var
            args[builtins.MSG] = ctx.msg_var
            args[builtins.BLOCK] = ctx.block_var
            locals = {name: self._translate_var(var, ctx) for name, var in function.local_vars.items()}
            ctx.args = args
            ctx.locals = locals
            ctx.all_vars = {**args, **locals}

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

            pres = ctx.permissions + ctx.immutable_permissions

            body = []

            # Assume all unchecked invariants
            unchecked_invs = [self.viper_ast.Inhale(inv) for inv in ctx.unchecked_invariants]
            body.extend(self._seqn_with_info(unchecked_invs, "Assume all unchecked invariants"))

            argument_conds = []
            for var in function.args.values():
                local_var = args[var.name].localVar()
                non_negs = self.type_translator.non_negative(local_var, var.type, ctx)
                arr_lens = self.type_translator.array_length(local_var, var.type, ctx)
                argument_conds.extend(non_negs)
                argument_conds.extend(arr_lens)

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

            # Introduce old_self
            old_self = builtins.old_self_var(self.viper_ast)
            ctx.new_local_vars.append(old_self)
            copy_old_stmts = []
            for field in ctx.fields.values():
                old_acc = self.viper_ast.FieldAccess(old_self.localVar(), field)
                perm = self.viper_ast.FieldAccessPredicate(old_acc, self.viper_ast.FullPerm())
                body.append(self.viper_ast.Inhale(perm))
                self_var = builtins.self_var(self.viper_ast).localVar()
                self_acc = self.viper_ast.FieldAccess(self_var, field)
                copy_old_stmts.append(self.viper_ast.FieldAssign(old_acc, self_acc))

            copy_old = self._seqn_with_info(copy_old_stmts, "New old state")
            ctx.copy_old = copy_old
            body.extend(copy_old)

            def returnBool(value: bool) -> Stmt:
                local_var = success_var.localVar()
                lit = self.viper_ast.TrueLit if value else self.viper_ast.FalseLit
                return self.viper_ast.LocalVarAssign(local_var, lit())

            # If we do not encounter an exception we will return success
            body.append(returnBool(True))

            # In the initializer initialize all fields to their default values
            if function.name == names.INIT:
                defaults = []
                for name, field in ctx.fields.items():
                    if name == names.SELF_BALANCE:
                        continue
                    field_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), field)
                    type = ctx.program.state[name].type
                    stmts, expr = self.type_translator.default_value(None, type, ctx)
                    assign = self.viper_ast.FieldAssign(field_acc, expr)
                    defaults += stmts + [assign]

                body.extend(self._seqn_with_info(defaults, "Assign default values to state vars"))

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
                balance_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), ctx.balance_field)
                inc_sum = self.viper_ast.Add(balance_acc, value_acc)
                payable_info = self.to_info(["Fuction is payable"])
                inc = self.viper_ast.FieldAssign(balance_acc, inc_sum, info=payable_info)
                body.append(inc)

                # Increase received for msg.sender by msg.value
                msg_sender = builtins.msg_sender_field_acc(self.viper_ast)
                rec = builtins.self_received_field_acc(self.viper_ast)
                rec_acc = builtins.self_received_map_get(self.viper_ast, msg_sender)
                rec_inc_sum = self.viper_ast.Add(rec_acc, value_acc)
                rec_set = builtins.self_received_map_set(self.viper_ast, msg_sender, rec_inc_sum)
                rec_inc = self.viper_ast.FieldAssign(rec, rec_set)
                body.append(rec_inc)

            body_stmts = self.statement_translator.translate_stmts(function.node.body, ctx)
            body.extend(self._seqn_with_info(body_stmts, "Function body"))

            # If we reach this point do not revert the state
            body.append(self.viper_ast.Goto(ctx.end_label))
            # Revert the state
            body.append(revert_label)
            # Return False
            body.append(returnBool(False))
            # Revert the fields, the return value does not have to be havoced because
            # it was never assigned to
            for name, field in ctx.fields.items():
                type = ctx.program.state[name].type
                body += self.type_translator.revert(type, field, ctx)

            # The end of a program, label where return statements jump to
            body.append(end_label)

            # Postconditions hold for single transactions, invariants across transactions.
            # Therefore, after the function execution the following steps happen:
            #   - Assert the specified postconditions of the function
            #   - Havoc self.balance
            #   - Assert invariants
            # This is necessary because a contract may receive additional money through
            # seldestruct or mining

            # First the postconditions are asserted
            posts = []
            # Postconditions are asserted with normal old expressions
            for post in function.postconditions:
                cond = self.specification_translator.translate_postcondition(post, ctx)
                post_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL)
                posts.append(self.viper_ast.Assert(cond, post_pos))

            for post in ctx.program.general_postconditions:
                cond = self.specification_translator.translate_postcondition(post, ctx, is_init)
                post_pos = self.to_position(post, ctx)
                if is_init:
                    succ = self.viper_ast.LocalVar(success_var.name(), success_var.typ(), post_pos)
                    succ_post = self.viper_ast.Implies(succ, cond, post_pos)
                    post_pos_r = self.to_position(post, ctx, rules.POSTCONDITION_FAIL)
                    posts.append(self.viper_ast.Assert(succ_post, post_pos_r))
                else:
                    via = [('general postcondition', post_pos)]
                    func_pos = self.to_position(function.node, ctx, rules.POSTCONDITION_FAIL, via)
                    posts.append(self.viper_ast.Assert(cond, func_pos))

            body.extend(self._seqn_with_info(posts, "Assert postconditions"))

            # Havoc self.balance
            balance_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), ctx.balance_field)
            body.extend(self._havoc_uint(balance_acc, ctx))

            # If the function is public we also assert the invariants
            # Invariants if we don't fail: old == last old we encountered
            # We use the special $old_self variable
            invariant_assertions = []
            # Invariants if we fail: old == beginning of the function
            # For that we can use the normal old
            invariant_assertions_fail = []
            translate_inv = self.specification_translator.translate_invariant
            for inv in ctx.program.invariants:
                with use_old_scope(False, ctx):
                    expr = translate_inv(inv, ctx, False, is_init)
                fail = translate_inv(inv, ctx, False, is_init)

                # If we have a synthesized __init__ we only create an
                # error message on the invariant
                # Additionally, invariants only have to hold on success
                if is_init:
                    apos = self.to_position(inv, ctx, rules.INVARIANT_FAIL)
                else:
                    via = [('invariant', expr.pos())]
                    apos = self.to_position(function.node, ctx, rules.INVARIANT_FAIL, via)

                assertion = self.viper_ast.Assert(expr, apos)
                fail_assertion = self.viper_ast.Assert(fail, apos)
                invariant_assertions.append(assertion)
                invariant_assertions_fail.append(fail_assertion)

            inv_info = self.to_info(["Assert invariants"])
            if_stmt = self.viper_ast.If(success_var.localVar(), invariant_assertions, invariant_assertions_fail)
            body.append(self.viper_ast.Seqn([if_stmt], info=inv_info))

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
            msg_name = ctx.inline_prefix() + builtins.MSG
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
                ret_name = ctx.inline_prefix() + builtins.RESULT_VAR
                ret_var_decl = self.viper_ast.LocalVarDecl(ret_name, ret_type, pos)
                ctx.new_local_vars.append(ret_var_decl)
                ctx.result_var = ret_var_decl
                ret_var = ret_var_decl.localVar()
            else:
                ret_var = None

            # Define end label for inlined return statements
            end_label_name = ctx.inline_prefix() + builtins.END_LABEL
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
        name = ctx.inline_prefix() + builtins.local_var_name(var.name)
        return self.viper_ast.LocalVarDecl(name, type, pos)

    def _non_negative(self, var, ctx: Context) -> Stmt:
        zero = self.viper_ast.IntLit(0)
        return self.viper_ast.GeCmp(var, zero)

    def _assume_non_negative(self, var, ctx: Context) -> Stmt:
        gez = self._non_negative(var, ctx)
        return self.viper_ast.Inhale(gez)

    def _seqn_with_info(self, stmts: [Stmt], comment: str) -> [Stmt]:
        if not stmts:
            return stmts
        info = self.to_info([comment])
        return [self.viper_ast.Seqn(stmts, info=info)]

    def _havoc_uint(self, field_acc, ctx: Context) -> List[Stmt]:
        havoc_name = ctx.new_local_var_name('havoc')
        havoc = self.viper_ast.LocalVarDecl(havoc_name, self.viper_ast.Int)
        ctx.new_local_vars.append(havoc)
        assume_pos = self._assume_non_negative(havoc.localVar(), ctx)
        inc = self.viper_ast.Add(field_acc, havoc.localVar())
        assign = self.viper_ast.FieldAssign(field_acc, inc)
        return [assume_pos, assign]

    def _create_field_access_predicate(self, field_access, amount, ctx: Context):
        if amount == 1:
            perm = self.viper_ast.FullPerm()
        else:
            perm = builtins.read_perm(self.viper_ast)
        return self.viper_ast.FieldAccessPredicate(field_access, perm)
