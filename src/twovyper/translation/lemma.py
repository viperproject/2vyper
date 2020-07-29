"""
Copyright (c) 2020 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.nodes import VyperFunction, VyperVar

from twovyper.translation import mangled
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context
from twovyper.translation.specification import SpecificationTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Function


class LemmaTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def translate(self, function: VyperFunction, ctx: Context) -> Function:
        with ctx.function_scope():
            with ctx.lemma_scope():
                # TODO: add rules for pre- and post-condition
                pos = self.to_position(function.node, ctx)

                ctx.function = function

                args = {name: self._translate_non_local_var(var, ctx) for name, var in function.args.items()}
                state = {names.SELF: TranslatedVar(names.SELF, mangled.present_state_var_name(names.SELF),
                                                   types.AnyStructType(), self.viper_ast, pos)}
                ctx.present_state = state
                ctx.old_state = ctx.present_state
                ctx.pre_state = ctx.present_state
                ctx.issued_state = ctx.present_state
                ctx.current_state = ctx.present_state
                ctx.current_old_state = ctx.present_state

                ctx.args = args.copy()
                ctx.locals = {}

                ctx.success_var = None
                ctx.return_label = None
                ctx.revert_label = None
                ctx.result_var = None

                preconditions = []
                # Type assumptions for arguments
                for var in function.args.values():
                    local_var = args[var.name].local_var(ctx)
                    assumptions = self.type_translator.type_assumptions(local_var, var.type, ctx)
                    preconditions.extend(assumptions)

                # Explicit preconditions
                for precondition in function.preconditions:
                    stmts = []
                    preconditions.append(self.specification_translator
                                         .translate_pre_or_postcondition(precondition, stmts, ctx))
                    assert not stmts

                postconditions = []
                for stmt in function.node.body:
                    assert isinstance(stmt, ast.ExprStmt)
                    expr = stmt.value
                    stmts = []
                    postconditions.append(self.specification_translator.translate(expr, stmts, ctx))
                    assert not stmts

                args_list = [arg.var_decl(ctx) for arg in args.values()]
                viper_name = mangled.lemma_name(function.name)
                function = self.viper_ast.Function(viper_name, args_list, self.viper_ast.Bool,
                                                   preconditions, postconditions, self.viper_ast.TrueLit(), pos)
        return function

    def _translate_non_local_var(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        name = mangled.local_var_name(ctx.inline_prefix, var.name)
        return TranslatedVar(var.name, name, var.type, self.viper_ast, pos, is_local=False)
