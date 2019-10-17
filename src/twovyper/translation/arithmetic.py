"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import List

from twovyper.ast import names
from twovyper.ast import types
from twovyper.ast.types import PrimitiveType, BoundedType

from twovyper.translation import helpers
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context

from twovyper.utils import switch

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt, StmtsAndExpr


class ArithmeticTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

        self._operations = {
            ast.USub: self.viper_ast.Minus,
            ast.Add: self.viper_ast.Add,
            ast.Sub: self.viper_ast.Sub,
            ast.Mult: self.viper_ast.Mul,
            # Note that / and % in Vyper means truncating division
            ast.Div: lambda l, r, pos, info: helpers.div(viper_ast, l, r, pos, info),
            ast.Mod: lambda l, r, pos, info: helpers.mod(viper_ast, l, r, pos, info),
            ast.Pow: lambda l, r, pos, info: helpers.pow(viper_ast, l, r, pos, info)
        }

    def uop(self, op, arg, otype: PrimitiveType, ctx: Context, pos=None, info=None) -> StmtsAndExpr:
        res = self._operations[type(op)](arg, pos, info)
        stmts = []
        # Unary negation can only overflow if one negates MIN_INT128
        if types.is_bounded(otype):
            oc = self.check_overflow(res, otype, ctx, pos)
            stmts.extend(oc)

        return stmts, res

    # Decimals are scaled integers, i.e. the decimal 2.3 is represented as the integer
    # 2.3 * 10^10 = 23000000000. For addition, subtraction, and modulo the same operations
    # as with integers can be used. For multiplication we need to divide out one of the
    # scaling factors while in division we need to multiply one in.

    def decimal_mult(self, lhs, rhs, ctx: Context, pos=None, info=None) -> Expr:
        scaling_factor = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
        mult = self.viper_ast.Mul(lhs, rhs, pos)
        # In decimal multiplication we divide the end result by the scaling factor
        return helpers.div(self.viper_ast, mult, scaling_factor, pos, info)

    def decimal_div(self, lhs, rhs, ctx: Context, pos=None, info=None) -> Expr:
        scaling_factor = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
        # In decimal division we first multiply the lhs by the scaling factor
        mult = self.viper_ast.Mul(lhs, scaling_factor, pos)
        return helpers.div(self.viper_ast, mult, rhs, pos, info)

    def binop(self, lhs, op: ast.operator, rhs, otype: PrimitiveType, ctx: Context, pos=None, info=None) -> StmtsAndExpr:
        stmts = []
        with switch(type(op), otype) as case:
            from twovyper.utils import _

            if case(ast.Div, _) or case(ast.Mod, _):
                cond = self.viper_ast.EqCmp(rhs, self.viper_ast.IntLit(0, pos), pos)
                stmts.append(self.fail_if(cond, [], ctx, pos))

            if case(ast.Mult, types.VYPER_DECIMAL):
                res = self.decimal_mult(lhs, rhs, ctx, pos, info)
            elif case(ast.Div, types.VYPER_DECIMAL):
                res = self.decimal_div(lhs, rhs, ctx, pos, info)
            else:
                res = self._operations[type(op)](lhs, rhs, pos, info)

        if types.is_bounded(otype):
            stmts.extend(self.check_under_overflow(res, otype, ctx, pos))

        return stmts, res

    def _set_overflow_flag(self, pos=None, info=None):
        overflow = helpers.overflow_var(self.viper_ast, pos).localVar()
        true_lit = self.viper_ast.TrueLit(pos)
        return self.viper_ast.LocalVarAssign(overflow, true_lit, pos, info)

    def check_underflow(self, arg, type: BoundedType, ctx: Context, pos=None, info=None) -> List[Stmt]:
        lower = self.viper_ast.IntLit(type.lower, pos)
        lt = self.viper_ast.LtCmp(arg, lower, pos)

        if types.is_unsigned(type):
            return [self.fail_if(lt, [], ctx, pos, info)]
        elif ctx.program.config.has_option(names.CONFIG_NO_OVERFLOWS):
            return []
        else:
            stmts = [self._set_overflow_flag(pos)]
            return [self.fail_if(lt, stmts, ctx, pos, info)]

    def check_overflow(self, arg, type: BoundedType, ctx: Context, pos=None, info=None) -> List[Stmt]:
        upper = self.viper_ast.IntLit(type.upper, pos)
        gt = self.viper_ast.GtCmp(arg, upper, pos)

        if ctx.program.config.has_option(names.CONFIG_NO_OVERFLOWS):
            return []
        else:
            stmts = [self._set_overflow_flag(pos)]
            return [self.fail_if(gt, stmts, ctx, pos, info)]

    def check_under_overflow(self, arg, type: BoundedType, ctx: Context, pos=None, info=None) -> List[Stmt]:
        if types.is_unsigned(type):
            underflow = self.check_underflow(arg, type, ctx, pos, info)
            overflow = self.check_overflow(arg, type, ctx, pos, info)
            return underflow + overflow
        elif ctx.program.config.has_option(names.CONFIG_NO_OVERFLOWS):
            return []
        else:
            lower = self.viper_ast.IntLit(type.lower, pos)
            upper = self.viper_ast.IntLit(type.upper, pos)

            lt = self.viper_ast.LtCmp(arg, lower, pos)
            gt = self.viper_ast.GtCmp(arg, upper, pos)

            cond = self.viper_ast.Or(lt, gt, pos)
            stmts = [self._set_overflow_flag(pos)]
            return [self.fail_if(cond, stmts, ctx, pos, info)]
