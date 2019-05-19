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
from nagini_translation.translation.context import Context, function_scope, use_old_scope

from nagini_translation.translation import builtins

from nagini_translation.viper.ast import ViperAST
from nagini_translation.viper.typedefs import Method, Stmt

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

            def returnBool(value: bool) -> Stmt:
                local_var = success_var.localVar()
                lit = self.viper_ast.TrueLit if value else self.viper_ast.FalseLit
                return self.viper_ast.LocalVarAssign(local_var, lit())

            # If we do not encounter an exception we will return success
            body = [returnBool(True)]

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
            info_msg = "Assume non-negativeness of uint256 and sizes of array args"
            body.extend(self._seqn_with_info(argument_cond_assumes, info_msg))

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
                balance_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), ctx.balance_field)
                inc_sum = self.viper_ast.Add(balance_acc, value_acc)
                payable_info = self.to_info(["Fuction is payable"])
                inc = self.viper_ast.FieldAssign(balance_acc, inc_sum, info=payable_info)
                body.append(inc)

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
            #   - Havoc variables like block.timestamp or self.balance
            #   - Assert invariants
            # This is necessary to not be able to prove the invariant
            # old(block.timestamp) == block.timestamp

            # First the postconditions are asserted
            post_assertions = []
            posts = []
            # Postconditions are asserted with normal old expressions
            for post in function.postconditions:
                cond = self.specification_translator.translate_postcondition(post, ctx)
                posts.append(cond)
                post_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL)
                post_assertions.append(self.viper_ast.Assert(cond, post_pos))

            for post in ctx.program.general_postconditions:
                cond = self.specification_translator.translate_postcondition(post, ctx, is_init)
                post_pos = self.to_position(post, ctx)
                if is_init:
                    succ = self.viper_ast.LocalVar(success_var.name(), success_var.typ(), post_pos)
                    succ_post = self.viper_ast.Implies(succ, cond, post_pos)
                    posts.append(succ_post)
                    post_pos_r = self.to_position(post, ctx, rules.POSTCONDITION_FAIL)
                    post_assertions.append(self.viper_ast.Assert(succ_post, post_pos_r))
                else:
                    posts.append(cond)
                    via = [('general postcondition', post_pos)]
                    func_pos = self.to_position(function.node, ctx, rules.POSTCONDITION_FAIL, via)
                    post_assertions.append(self.viper_ast.Assert(cond, func_pos))

            body.extend(self._seqn_with_info(post_assertions, "Assert postconditions"))

            # Havoc block.timestamp
            block_timestamp = builtins.block_timestamp_field(self.viper_ast)
            time_acc = self.viper_ast.FieldAccess(ctx.block_var.localVar(), block_timestamp)
            body.extend(self._havoc_uint(time_acc, ctx))
            # Havoc self.balance
            balance_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), ctx.balance_field)
            body.extend(self._havoc_uint(balance_acc, ctx))

            # If the function is public we also assert the invariants
            invariants = []
            # Invariants if we don't fail: old == last old we encountered
            # We use the special $old_self variable
            invariant_assertions = []
            # Invariants if we fail: old == beginning of the function
            # For that we can use the normal old
            invariant_assertions_fail = []
            translate_inv = self.specification_translator.translate_invariant
            if function.is_public():
                for inv in ctx.program.invariants:
                    with use_old_scope(False, ctx):
                        expr = translate_inv(inv, ctx, False, is_init)
                    fail = translate_inv(inv, ctx, False, is_init)
                    invariants.append(fail)

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

            # If the return value is of type uint256 add non-negativeness to
            # poscondition, but don't assert it (as it always holds anyway)
            # If the return value is an array, add size to postconditions
            ret_posts = []
            if function.type.return_type:
                ret_var_local = ret_var.localVar()
                non_negs = self.type_translator.non_negative(ret_var_local, function.type.return_type, ctx)
                arr_lens = self.type_translator.array_length(ret_var_local, function.type.return_type, ctx)
                ret_posts.extend(non_negs)
                ret_posts.extend(arr_lens)

            # Postconditions are:
            #   - The permissions that are passed around
            #   - The unchecked invariants
            #   - The assumptions about non-negativeness and size of arguments (needed for well-definedness) TODO: reevaluate once function calling is supported
            #   - An assumption about non-negativeness for uint256 results and size for array results
            #   - The postconditions specified by the user
            #   - The invariants
            perms = ctx.permissions + ctx.immutable_permissions
            all_posts = perms + ctx.unchecked_invariants + argument_conds + ret_posts + posts + invariants

            # Add preconditions; invariants do not have to hold before __init__
            inv_pres = ctx.invariants(is_pre=True, is_init=is_init)
            translate_pre = self.specification_translator.translate_precondition
            pres = [translate_pre(pre, ctx) for pre in function.preconditions]
            # Preconditions are:
            #   - The permissions that are passed around
            #   - The preconditions are were specified by the user
            #   - The invariants
            # Note: Unchecked invariants are assumed at the beginning so they do not have to
            # be checked on a method call
            all_pres = ctx.permissions + ctx.immutable_permissions + pres + inv_pres

            # Since we check the postconditions and invariants in the body we can just assume
            # false, so the actual posconditions always succeed
            assume_false = self.viper_ast.Inhale(self.viper_ast.FalseLit())
            body.append(assume_false)

            args_list = list(args.values())
            locals_list = [*locals.values(), *ctx.new_local_vars]

        method = self.viper_ast.Method(function.name, args_list, rets, all_pres, all_posts, locals_list, body, pos)
        return method

    def _translate_var(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        type = self.type_translator.translate(var.type, ctx)
        return self.viper_ast.LocalVarDecl(var.name, type, pos)

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
