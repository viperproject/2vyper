"""
Copyright (c) 2020 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from functools import reduce
from typing import List

from twovyper.ast.types import VYPER_BOOL

from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.arithmetic import ArithmeticTranslator
from twovyper.translation.context import Context
from twovyper.translation.expression import ExpressionTranslator
from twovyper.translation.specification import SpecificationTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedPureIndexedVar

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


class PureTranslatorMixin(CommonTranslator):

    def seqn_with_info(self, expressions: [Expr], comment: str, res: List[Expr]):
        res.extend(expressions)

    def fail_if(self, cond: Expr, stmts: List[Stmt], res: List[Expr], ctx: Context, pos=None, info=None):
        assert isinstance(ctx.success_var, TranslatedPureIndexedVar)

        var = TranslatedPureIndexedVar('cond', 'cond', VYPER_BOOL, self.viper_ast, pos)
        res.append(self.viper_ast.EqCmp(var.local_var(ctx), cond))

        # Fail if the condition is true
        fail_cond = reduce(self.viper_ast.And, ctx.pure_conds + [var.local_var(ctx)])
        old_success_idx = ctx.success_var.evaluate_idx(ctx)
        ctx.success_var.new_idx()
        expr = self.viper_ast.EqCmp(ctx.success_var.local_var(ctx), self.viper_ast.FalseLit())
        res.append(self.viper_ast.Implies(fail_cond, expr, pos, info))
        ctx.pure_success.append((fail_cond, ctx.success_var.evaluate_idx(ctx)))
        ctx.success_var.idx = old_success_idx

        # If we did not fail, we know that the condition is not true
        ctx.pure_conds.append(self.viper_ast.Not(var.local_var(ctx)))


class PureArithmeticTranslator(PureTranslatorMixin, ArithmeticTranslator):
    pass


class PureExpressionTranslator(PureTranslatorMixin, ExpressionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.arithmetic_translator = PureArithmeticTranslator(viper_ast, self.no_reverts)
        self.type_translator = PureTypeTranslator(viper_ast)

    @property
    def spec_translator(self):
        return PureSpecificationTranslator(self.viper_ast)

    @property
    def function_translator(self):
        from twovyper.translation.pure_function import PureFunctionTranslator
        return PureFunctionTranslator(self.viper_ast)


class PureSpecificationTranslator(PureTranslatorMixin, SpecificationTranslator):
    pass


class PureTypeTranslator(PureTranslatorMixin, TypeTranslator):
    pass
