"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Dict

from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import Method, Stmt

from nagini_translation.ast import names
from nagini_translation.ast import types
from nagini_translation.ast.nodes import VyperFunction, VyperVar

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.statement import StatementTranslator
from nagini_translation.translation.specification import SpecificationTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.context import Context, function_scope, via_scope

from nagini_translation.translation import builtins


class FunctionTranslator(NodeTranslator):

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

            args = {name: self._translate_var(var, ctx) for name, var in function.args.items()}
            args[builtins.SELF] = ctx.self_var
            args[builtins.MSG] = ctx.msg_var
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

            if function.ret:
                ret_type = self.type_translator.translate(function.ret, ctx)
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
            for inv in ctx.unchecked_invariants:
                body.append(self.viper_ast.Inhale(inv))
            
            # Assume for all uint256 arguments a that a >= 0
            for var in function.args.values():
                if var.type == types.VYPER_UINT256:
                    body.append(self._assume_non_negative(args[var.name].localVar(), ctx))

            # In the initializer initialize all fields to their default values
            if function.name == names.INIT:
                for name, field in ctx.fields.items():
                    field_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), field)
                    type = ctx.program.state[name].type
                    stmts, expr = self.type_translator.translate_default_value(type, ctx)
                    assign = self.viper_ast.FieldAssign(field_acc, expr)
                    body += stmts + [assign]

            body += self.statement_translator.translate_stmts(function.node.body, ctx)
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

            # The end of a program, label where return statements jump to
            body.append(end_label)

            # Postconditions hold for single transactions, invariants across transactions.
            # Therefore, after the function execution the following steps happen:
            #   - Assert the specified postconditions of the function
            #   - Havoc variables like block.timestamp or msg.sender
            #   - Assert invariants
            # This is necessary to not be able to prove the invariant 
            # old(block.timestamp) == block.timestamp

            # First the postconditions are asserted
            posts, post_assertions = self.specification_translator.translate_postconditions(function.postconditions, ctx)
            body += post_assertions
            # If the function is public we also assert the invariants
            if function.is_public():
                translator = self.specification_translator
                is_init = function.name == names.INIT
                with via_scope(ctx):
                    if not is_init:
                        ctx.vias = [('invariant', pos)]
                    invariants, invariant_assertions = translator.translate_invariants(ctx.program.invariants, ctx, is_init)
                body += invariant_assertions
            else:
                invariants = []

            # If the return value is of type uint256 add non-negativeness to
            # poscondition, but don't assert it (as it always holds anyway)
            ret_post = []
            if function.ret == types.VYPER_UINT256:
                ret_post.append(self._non_negative(ret_var.localVar(), ctx))

            # Postconditions are:
            #   - The permissings that are passed around
            #   - The unchecked invariants
            #   - An assumption about non-negativeness for uint256 results
            #   - The postconditions specified by the user
            #   - The invariants
            all_posts = ctx.permissions + ctx.unchecked_invariants + ret_post + posts + invariants

            # Add preconditions; invariants do not have to hold before __init__
            inv_pres = self.specification_translator.translate_preconditions(ctx.program.invariants, ctx)
            inv_pres = [] if function.name == names.INIT else inv_pres
            pres = self.specification_translator.translate_preconditions(function.preconditions, ctx)
            # Preconditions are: 
            #   - The permissions that are passed around
            #   - The preconditions are were specified by the user
            #   - The invariants
            # Note: Unchecked invariants are assumed at the beginning so they do not have to
            # be checked on a method call
            all_pres = ctx.permissions + pres + inv_pres

            # Since we check the postconditions and invariants in the body we can just assume
            # false, so the actual posconditions always succeed
            assume_false = self.viper_ast.Inhale(self.viper_ast.FalseLit())
            body.append(assume_false)

            seqn = self.viper_ast.Seqn(body, pos)
            args_list = list(args.values())
            new_locals = ctx.new_local_vars
            locals_list = list(locals.values()) + new_locals
            
        method = self.viper_ast.Method(function.name, args_list, rets, all_pres, all_posts, locals_list, seqn, pos)
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
