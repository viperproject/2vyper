"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.types import PrimitiveType, BoundedType

from twovyper.translation import helpers
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context

from twovyper.utils import switch

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt
from twovyper.vyper import is_compatible_version


class ArithmeticTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST, no_reverts: bool = False):
        super().__init__(viper_ast)
        self.no_reverts = no_reverts

        self._unary_arithmetic_operations = {
            ast.UnaryArithmeticOperator.ADD: lambda o, pos: o,
            ast.UnaryArithmeticOperator.SUB: self.viper_ast.Minus
        }

        self._arithmetic_ops = {
            ast.ArithmeticOperator.ADD: self.viper_ast.Add,
            ast.ArithmeticOperator.SUB: self.viper_ast.Sub,
            ast.ArithmeticOperator.MUL: self.viper_ast.Mul,
            # Note that / and % in Vyper means truncating division
            ast.ArithmeticOperator.DIV: lambda l, r, pos: helpers.div(viper_ast, l, r, pos),
            ast.ArithmeticOperator.MOD: lambda l, r, pos: helpers.mod(viper_ast, l, r, pos),
            ast.ArithmeticOperator.POW: lambda l, r, pos: helpers.pow(viper_ast, l, r, pos),
        }

        self._wrapped_arithmetic_ops = {
            ast.ArithmeticOperator.ADD: self.viper_ast.Add,
            ast.ArithmeticOperator.SUB: self.viper_ast.Sub,
            ast.ArithmeticOperator.MUL: lambda l, r, pos: helpers.w_mul(viper_ast, l, r, pos),
            ast.ArithmeticOperator.DIV: lambda l, r, pos: helpers.w_div(viper_ast, l, r, pos),
            ast.ArithmeticOperator.MOD: lambda l, r, pos: helpers.w_mod(viper_ast, l, r, pos),
            ast.ArithmeticOperator.POW: lambda l, r, pos: helpers.pow(viper_ast, l, r, pos),
        }

        self.non_linear_ops = {
            ast.ArithmeticOperator.MUL,
            ast.ArithmeticOperator.DIV,
            ast.ArithmeticOperator.MOD
        }

    def is_wrapped(self, val):
        return hasattr(val, 'isSubtype') and val.isSubtype(helpers.wrapped_int_type(self.viper_ast))

    def is_unwrapped(self, val):
        return hasattr(val, 'isSubtype') and val.isSubtype(self.viper_ast.Int)

    def unary_arithmetic_op(self, op: ast.UnaryArithmeticOperator, arg, otype: PrimitiveType, res: List[Stmt],
                            ctx: Context, pos=None) -> Expr:
        result = self._unary_arithmetic_operations[op](arg, pos)
        # Unary negation can only overflow if one negates MIN_INT128
        if types.is_bounded(otype):
            assert isinstance(otype, BoundedType)
            self.check_overflow(result, otype, res, ctx, pos)

        return result

    # Decimals are scaled integers, i.e. the decimal 2.3 is represented as the integer
    # 2.3 * 10^10 = 23000000000. For addition, subtraction, and modulo the same operations
    # as with integers can be used. For multiplication we need to divide out one of the
    # scaling factors while in division we need to multiply one in.

    def _decimal_mul(self, lhs, rhs, pos=None, info=None) -> Expr:
        scaling_factor = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
        mult = self.viper_ast.Mul(lhs, rhs, pos)
        # In decimal multiplication we divide the end result by the scaling factor
        return helpers.div(self.viper_ast, mult, scaling_factor, pos, info)

    def _wrapped_decimal_mul(self, lhs, rhs, pos=None, info=None) -> Expr:
        scaling_factor = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
        mult = helpers.w_mul(self.viper_ast, lhs, rhs, pos)
        uw_mult = helpers.w_unwrap(self.viper_ast, mult, pos)
        rescaled_mult = helpers.div(self.viper_ast, uw_mult, scaling_factor, pos, info)
        return helpers.w_wrap(self.viper_ast, rescaled_mult, pos)

    def _decimal_div(self, lhs, rhs, pos=None, info=None) -> Expr:
        scaling_factor = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
        # In decimal division we first multiply the lhs by the scaling factor
        mult = self.viper_ast.Mul(lhs, scaling_factor, pos)
        return helpers.div(self.viper_ast, mult, rhs, pos, info)

    def _wrapped_decimal_div(self, lhs, rhs, pos=None, info=None) -> Expr:
        scaling_factor = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
        uw_lhs = helpers.w_unwrap(self.viper_ast, lhs, pos)
        uw_mult = self.viper_ast.Mul(uw_lhs, scaling_factor, pos)
        mult = helpers.w_wrap(self.viper_ast, uw_mult, pos)
        return helpers.w_div(self.viper_ast, mult, rhs, pos, info)

    def arithmetic_op(self, lhs, op: ast.ArithmeticOperator, rhs, otype: PrimitiveType, res: List[Stmt],
                      ctx: Context, pos=None) -> Expr:
        ast_op = ast.ArithmeticOperator
        left_is_wrapped = self.is_wrapped(lhs)
        right_is_wrapped = self.is_wrapped(rhs)
        if ctx.inside_interpreted:
            if left_is_wrapped:
                left_is_wrapped = False
                lhs = helpers.w_unwrap(self.viper_ast, lhs, pos)
            if right_is_wrapped:
                right_is_wrapped = False
                rhs = helpers.w_unwrap(self.viper_ast, rhs, pos)
        elif ctx.inside_lemma:
            if not left_is_wrapped:
                left_is_wrapped = True
                lhs = helpers.w_wrap(self.viper_ast, lhs, pos)
            if not right_is_wrapped:
                right_is_wrapped = True
                rhs = helpers.w_wrap(self.viper_ast, rhs, pos)
        with switch(op, otype) as case:
            from twovyper.utils import _

            if (case(ast_op.DIV, _) or case(ast_op.MOD, _)) and not self.no_reverts:
                expr = rhs
                if right_is_wrapped:
                    expr = helpers.w_unwrap(self.viper_ast, rhs, pos)
                cond = self.viper_ast.EqCmp(expr, self.viper_ast.IntLit(0, pos), pos)
                self.fail_if(cond, [], res, ctx, pos)

            if left_is_wrapped and right_is_wrapped:
                # Both are wrapped
                if case(ast_op.MUL, types.VYPER_DECIMAL):
                    expr = self._wrapped_decimal_mul(lhs, rhs, pos)
                elif case(ast_op.DIV, types.VYPER_DECIMAL):
                    expr = self._wrapped_decimal_div(lhs, rhs, pos)
                else:
                    expr = self._wrapped_arithmetic_ops[op](lhs, rhs, pos)
            else:
                if case(ast_op.MUL, types.VYPER_DECIMAL):
                    expr = self._decimal_mul(lhs, rhs, pos)
                elif case(ast_op.DIV, types.VYPER_DECIMAL):
                    expr = self._decimal_div(lhs, rhs, pos)
                else:
                    expr = self._arithmetic_ops[op](lhs, rhs, pos)

        if types.is_bounded(otype):
            assert isinstance(otype, BoundedType)
            if is_compatible_version('<=0.1.0-beta.17') and op == ast_op.POW:
                # In certain versions of Vyper there was no overflow check for POW.
                self.check_underflow(expr, otype, res, ctx, pos)
            else:
                self.check_under_overflow(expr, otype, res, ctx, pos)

        return expr

    # Overflows and underflow checks can be disabled with the config flag 'no_overflows'.
    # If it is not enabled, we revert if an overflow happens. Additionally, we set the overflows
    # variable to true, which is used for success(if_not=overflow).
    #
    # Note that we only treat 'arbitary' bounds due to limited bit size as overflows,
    # getting negative unsigned values results in a normal revert.

    def _set_overflow_flag(self, res: List[Stmt], pos=None):
        overflow = helpers.overflow_var(self.viper_ast, pos).localVar()
        true_lit = self.viper_ast.TrueLit(pos)
        res.append(self.viper_ast.LocalVarAssign(overflow, true_lit, pos))

    def check_underflow(self, arg, otype: BoundedType, res: List[Stmt], ctx: Context, pos=None):
        lower = self.viper_ast.IntLit(otype.lower, pos)
        lt = self.viper_ast.LtCmp(arg, lower, pos)

        if types.is_unsigned(otype) and not self.no_reverts:
            self.fail_if(lt, [], res, ctx, pos)
        elif not self.no_reverts and not ctx.program.config.has_option(names.CONFIG_NO_OVERFLOWS):
            stmts = []
            self._set_overflow_flag(stmts, pos)
            self.fail_if(lt, stmts, res, ctx, pos)

    def check_overflow(self, arg, otype: BoundedType, res: List[Stmt], ctx: Context, pos=None):
        upper = self.viper_ast.IntLit(otype.upper, pos)
        gt = self.viper_ast.GtCmp(arg, upper, pos)

        if not self.no_reverts and not ctx.program.config.has_option(names.CONFIG_NO_OVERFLOWS):
            stmts = []
            self._set_overflow_flag(stmts, pos)
            self.fail_if(gt, stmts, res, ctx, pos)

    def check_under_overflow(self, arg, otype: BoundedType, res: List[Stmt], ctx: Context, pos=None):
        # For unsigned types we need to check over and underflow separately as we treat underflows
        # as normal reverts
        if types.is_unsigned(otype) and not self.no_reverts:
            self.check_underflow(arg, otype, res, ctx, pos)
            self.check_overflow(arg, otype, res, ctx, pos)
        elif not self.no_reverts and not ctx.program.config.has_option(names.CONFIG_NO_OVERFLOWS):
            # Checking for overflow and undeflow in the same if-condition is more efficient than
            # introducing two branches
            lower = self.viper_ast.IntLit(otype.lower, pos)
            upper = self.viper_ast.IntLit(otype.upper, pos)

            lt = self.viper_ast.LtCmp(arg, lower, pos)
            gt = self.viper_ast.GtCmp(arg, upper, pos)

            cond = self.viper_ast.Or(lt, gt, pos)
            stmts = []
            self._set_overflow_flag(stmts, pos)
            self.fail_if(cond, stmts, res, ctx, pos)
