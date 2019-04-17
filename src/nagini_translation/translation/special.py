"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Tuple, List

from nagini_translation.lib.typedefs import Expr, Stmt
from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.translation.context import Context
from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.expression import ExpressionTranslator


class SpecialTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.expression_translator = ExpressionTranslator(viper_ast)

    def translate_range(self, node: ast.Call, ctx: Context) -> Tuple[List[Stmt], Expr, int]:
        if len(node.args) == 1:
            # A range expression of the form 'range(n)' where 'n' is a constant
            pos = self.to_position(node)
            info = self.no_info()

            start = self.viper_ast.IntLit(0, pos, info)
            times = self.translate_constant(node.args[0], ctx)
            
            return [], start, times
        elif len(node.args) == 2:
            # A range expression of the form 'range(x, x + n)' where 'n' is a constant
            stmts, start = self.expression_translator.translate(node.args[0], ctx)
            times = self.translate_constant(node.args[1].right, ctx)

            return stmts, start, times
        else:
            # TODO: create exception for this
            raise AssertionError("Range has to have 1 or 2 arguments.")

    def translate_constant(self, node, ctx: Context):
        if isinstance(node, ast.Num):
            return node.n
        else:
            # TODO: create exception for this
            raise AssertionError("Constant not allowed")
