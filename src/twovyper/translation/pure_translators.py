"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

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

        cond_var = TranslatedPureIndexedVar('cond', 'cond', VYPER_BOOL, self.viper_ast, pos, info)
        cond_local_var = cond_var.local_var(ctx)
        assign = self.viper_ast.EqCmp(cond_local_var, cond, pos, info)
        expr = self.viper_ast.Implies(ctx.pure_conds, assign, pos, info) if ctx.pure_conds else assign
        res.append(expr)

        # Fail if the condition is true
        fail_cond = self.viper_ast.And(ctx.pure_conds, cond_local_var, pos, info) if ctx.pure_conds else cond_local_var
        old_success_idx = ctx.success_var.evaluate_idx(ctx)
        ctx.success_var.new_idx()
        assign = self.viper_ast.EqCmp(ctx.success_var.local_var(ctx), self.viper_ast.FalseLit(), pos, info)
        expr = self.viper_ast.Implies(ctx.pure_conds, assign, pos, info) if ctx.pure_conds else assign
        res.append(expr)
        ctx.pure_success.append((fail_cond, ctx.success_var.evaluate_idx(ctx)))
        ctx.success_var.idx = old_success_idx

        # If we did not fail, we know that the condition is not true
        negated_local_var = self.viper_ast.Not(cond_local_var, pos, info)
        ctx.pure_conds = self.viper_ast.And(ctx.pure_conds, negated_local_var, pos, info)\
            if ctx.pure_conds else negated_local_var


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
