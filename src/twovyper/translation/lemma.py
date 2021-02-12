"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.ast import ast_nodes as ast
from twovyper.ast.nodes import VyperFunction, VyperVar

from twovyper.translation import mangled
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context
from twovyper.translation.specification import SpecificationTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.verification import rules

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Function


class LemmaTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def translate(self, function: VyperFunction, ctx: Context) -> List[Function]:
        with ctx.function_scope():
            with ctx.lemma_scope():
                pos = self.to_position(function.node, ctx)

                ctx.function = function

                args = {name: self._translate_non_local_var(var, ctx) for name, var in function.args.items()}

                ctx.present_state = {}
                ctx.old_state = {}
                ctx.pre_state = {}
                ctx.issued_state = {}
                ctx.current_state = {}
                ctx.current_old_state = {}

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

                # If we assume uninterpreted function and assert the interpreted ones, the lemma has no body
                body = None if function.is_interpreted() else self.viper_ast.TrueLit()

                postconditions = []
                interpreted_postconditions = []
                if function.is_interpreted():
                    # Without a body, we must ensure that "result == true"
                    viper_result = self.viper_ast.Result(self.viper_ast.Bool, pos)
                    postconditions.append(self.viper_ast.EqCmp(viper_result, self.viper_ast.TrueLit(), pos))
                for idx, stmt in enumerate(function.node.body):
                    assert isinstance(stmt, ast.ExprStmt)
                    expr = stmt.value
                    stmts = []
                    post = self.specification_translator.translate(expr, stmts, ctx)
                    post_pos = self.to_position(stmt, ctx, rules=rules.LEMMA_FAIL)
                    viper_result = self.viper_ast.Result(self.viper_ast.Bool, post_pos)
                    postconditions.append(self.viper_ast.EqCmp(viper_result, post, post_pos))
                    if function.is_interpreted():
                        # If the function is interpreted, generate also an interpreted version of the lemma step
                        with ctx.interpreted_scope():
                            interpreted_post = self.specification_translator.translate(expr, stmts, ctx)
                            interpreted_postconditions.append(
                                self.viper_ast.EqCmp(viper_result, interpreted_post, post_pos))
                    assert not stmts

                args_list = [arg.var_decl(ctx) for arg in args.values()]
                viper_name = mangled.lemma_name(function.name)
                viper_functions = [self.viper_ast.Function(viper_name, args_list, self.viper_ast.Bool,
                                                           preconditions, postconditions, body, pos)]
                if function.is_interpreted():
                    # If we have interpreted postconditions, generate a second function.
                    # This second function has always a body, the same arguments and the same preconditions, but uses
                    # interpreted mul, div and mod instead of the uninterpreted $Int-functions in the postconditions.
                    viper_functions.append(self.viper_ast.Function(
                        "interpreted$" + viper_name, args_list, self.viper_ast.Bool, preconditions,
                        interpreted_postconditions, self.viper_ast.TrueLit(), pos))
        return viper_functions

    def _translate_non_local_var(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        name = mangled.local_var_name(ctx.inline_prefix, var.name)
        return TranslatedVar(var.name, name, var.type, self.viper_ast, pos, is_local=False)
