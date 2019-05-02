"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import List

from nagini_translation.ast import names

from nagini_translation.lib.errors import rules
from nagini_translation.lib.typedefs import Expr, StmtsAndExpr
from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.context import Context

from nagini_translation.errors.translation_exceptions import InvalidProgramException


class SpecificationTranslator(ExpressionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self._invariant_mode = None
        # We require history invariants to be reflexive, therefore we can simply
        # replace ignore expressions by their expression in preconditions and in the
        # postcondition of __init__
        self._ignore_old = None

    def translate_preconditions(self, pres: List[ast.AST], ctx: Context):
        self._invariant_mode = False
        self._ignore_old = True
        return self._translate_specification(pres, None, ctx)[0]

    def translate_postconditions(self, posts: List[ast.AST], ctx: Context):
        self._invariant_mode = False
        self._ignore_old = False
        rule = rules.POSTCONDITION_FAIL
        return self._translate_specification(posts, rule, ctx)

    def translate_invariants(self, invs: List[ast.AST], ctx: Context, ignore_old = False):
        self._invariant_mode = True
        self._ignore_old = ignore_old
        rule = rules.INVARIANT_FAIL
        return self._translate_specification(invs, rule, ctx)

    def _translate_specification(self, exprs: List[ast.AST], rule, ctx: Context):
        info = self.no_info()
        specs = []
        assertions = []
        for e in exprs:
            expr = self._translate_spec(e, ctx)
            apos = self.to_position(e, ctx, rule)
            assert_stmt = self.viper_ast.Assert(expr, apos, info)
            specs.append(expr)
            assertions.append(assert_stmt)
        
        return specs, assertions

    def _translate_spec(self, node, ctx: Context):
        _, expr = self.translate(node, ctx)
        return expr

    def translate_Call(self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        assert isinstance(node.func, ast.Name)

        pos = self.to_position(node, ctx)
        info = self.no_info()

        name = node.func.id
        if name == names.IMPLIES:
            if len(node.args) != 2:
                raise InvalidProgramException(node, "Implication requires 2 arguments.")
            
            lhs = self._translate_spec(node.args[0], ctx)
            rhs = self._translate_spec(node.args[1], ctx)

            implies = self.viper_ast.Or(self.viper_ast.Not(lhs, pos, info), rhs, pos, info)
            return [], implies
        elif name == names.RESULT or name == names.SUCCESS:
            cap = name.capitalize()
            if self._invariant_mode:
                raise InvalidProgramException(node, f"{cap} not allowed in invariant.")
            if node.args:
                raise InvalidProgramException(node, f"{cap} must not have arguments.")

            var = ctx.result_var if name == names.RESULT else ctx.success_var
            return [], var.localVar()
        elif name == names.OLD:
            if len(node.args) != 1:
                raise InvalidProgramException(node, "Old expression require a single argument.")
            
            expr = self._translate_spec(node.args[0], ctx)
            if self._ignore_old:
                return [], expr
            else:
                return [], self.viper_ast.Old(expr, pos, info)
        else:
            raise InvalidProgramException(node, f"Call to function {name} not allowed in specification.")

