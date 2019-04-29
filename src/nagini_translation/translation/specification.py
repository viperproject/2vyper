"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

import nagini_translation.lib.errors.rules as conversion_rules

from nagini_translation.lib.typedefs import StmtsAndExpr
from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.context import Context

from nagini_translation.errors.translation_exceptions import InvalidProgramException


class SpecificationTranslator(ExpressionTranslator):
    
    def __init__(self, viper_ast: ViperAST, invariant_mode: bool):
        super().__init__(viper_ast)
        self.invariant_mode = invariant_mode

    def translate_spec(self, node, ctx: Context):
        _, expr = self.translate(node, ctx)
        return expr

    def to_position(self, node: ast.AST, ctx: Context, rules = None, error_string = None):
        r = conversion_rules.INVARIANT_FAIL if self.invariant_mode else None
        return super().to_position(node, ctx, r, error_string)

    def translate_Name(self, node: ast.Name, ctx: Context) -> StmtsAndExpr:
        if self.invariant_mode:
            if node.id == 'self':
                return [], ctx.self_var.localVar()
            else:
                # TODO: is this always an error?
                assert False
        else:
            return super().translate_Name(node, ctx)

    def translate_Call(self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        assert isinstance(node.func, ast.Name)

        pos = self.to_position(node, ctx)
        info = self.no_info()

        name = node.func.id
        if name == 'result' or name == 'success':
            cap = name.capitalize()
            if self.invariant_mode:
                raise InvalidProgramException(node, f"{cap} not allowed in invariant.")
            if node.args:
                raise InvalidProgramException(node, f"{cap} must not have arguments.")

            var = ctx.result_var if name == 'result' else ctx.success_var
            return [], var.localVar()
        elif name == 'old':
            if len(node.args) != 1:
                raise InvalidProgramException(node, "Old expression require a single argument.")
            
            _, expr = self.translate(node.args[0], ctx)
            return [], self.viper_ast.Old(expr, pos, info)
        else:
            raise InvalidProgramException(node, f"Call to function {name} not allowed in specification.")

