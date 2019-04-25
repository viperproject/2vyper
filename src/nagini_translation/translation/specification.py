"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

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

    def translate_Call(self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        assert isinstance(node.func, ast.Name)

        pos = self.to_position(node, ctx)
        info = self.no_info()

        name = node.func.id
        if name == 'result':
            if self.invariant_mode:
                raise InvalidProgramException(node, "Result not allowed in invariant.")
            if node.args:
                raise InvalidProgramException(node, "Result must not have arguments.")

            return [], ctx.result_var.localVar()
        elif name == 'old':
            if len(node.args) != 1:
                raise InvalidProgramException(node, "Old expression require a single argument.")
            
            _, expr = self.translate(node.args[0], ctx)
            return [], self.viper_ast.Old(expr, pos, info)
        else:
            raise InvalidProgramException(node, f"Call to function {name} not allowed in specification.")

