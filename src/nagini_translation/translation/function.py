"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Dict

from nagini_translation.parsing.ast import VyperFunction, VyperVar
from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import Method, Stmt

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.statement import StatementTranslator
from nagini_translation.translation.specification import SpecificationTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.context import Context, function_scope

from nagini_translation.translation.builtins import INIT, SELF


class FunctionTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.statement_translator = StatementTranslator(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast, False)
        self.type_translator = TypeTranslator(viper_ast)

    def translate(self, function: VyperFunction, ctx: Context) -> Method:
        with function_scope(ctx):
            pos = self.to_position(function.node, ctx)
            nopos = self.no_position()
            info = self.no_info()

            ctx.function = function

            args = {name: self._translate_var(var, ctx) for name, var in function.args.items()}
            args[SELF] = ctx.self_var
            locals = {name: self._translate_var(var, ctx) for name, var in function.local_vars.items()}
            ctx.args = args
            ctx.locals = locals
            ctx.all_vars = {**args, **locals}

            success_var = self.viper_ast.LocalVarDecl('$succ', self.viper_ast.Bool, nopos, info)
            ctx.success_var = success_var
            revert_label = self.viper_ast.Label('revert', nopos, info)
            ctx.revert_label = 'revert'

            rets = [success_var]
            end_label = self.viper_ast.Label('end', pos, info)
            ctx.end_label = 'end'

            if function.ret:
                retType = self.type_translator.translate(function.ret, ctx)
                retVar = self.viper_ast.LocalVarDecl('$ret', retType, pos, info)
                rets.append(retVar)
                ctx.result_var = retVar

            def returnBool(value: bool) -> Stmt:
                local_var = success_var.localVar()
                lit = self.viper_ast.TrueLit if value else self.viper_ast.FalseLit
                return self.viper_ast.LocalVarAssign(local_var, lit(nopos, info), nopos, info)

            # If we do not encounter an exception we will return success
            body = [returnBool(True)]

            # In the initializer initialize all fields to their default values
            if function.name == INIT:
                for name, field in ctx.fields.items():
                    field_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), field, nopos, info)
                    type = ctx.program.state[name].type
                    stmts, expr = self.type_translator.translate_default_value(type, ctx)
                    assign = self.viper_ast.FieldAssign(field_acc, expr, nopos, info)
                    body += stmts + [assign]

            body += self.statement_translator.translate_stmts(function.node.body, ctx)
            # If we reach this point do not revert the state
            body.append(self.viper_ast.Goto(ctx.end_label, nopos, info))
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

            seqn = self.viper_ast.Seqn(body, pos, info)
            args_list = list(args.values())
            new_locals = ctx.new_local_vars
            locals_list = list(locals.values()) + new_locals

            # TODO: think about whether invariants should come first or second
            # TODO: implement via so that error messages for invariants include method that
            # violates it

            if function.is_public:
                # All invariants have to hold after all public functions
                posts = ctx.ghost_general_invariants + ctx.ghost_invariants + ctx.invariants
                # General invariants have to hold before every public function except __init__
                pres = ctx.ghost_general_invariants if function.name == INIT else posts.copy()
            else:
                # Private functions only use pre and post conditions that are specified
                pres = []
                posts = []

            pres += [self.specification_translator.translate_spec(p, ctx) for p in function.preconditions]
            posts += [self.specification_translator.translate_spec(p, ctx) for p in function.postconditions]
            
        method = self.viper_ast.Method(function.name, args_list, rets, pres, posts, locals_list, seqn, pos, info)
        return method
        

    def _translate_var(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        info = self.no_info()
        type = self.type_translator.translate(var.type, ctx)
        return self.viper_ast.LocalVarDecl(var.name, type, pos, info)
        