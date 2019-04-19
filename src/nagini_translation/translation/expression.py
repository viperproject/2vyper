"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast
import functools

from nagini_translation.lib.typedefs import StmtsAndExpr
from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.translation.context import Context


class ExpressionTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

        self._operations = {
            ast.USub: self.viper_ast.Minus,
            ast.Add: self.viper_ast.Add,
            ast.Sub: self.viper_ast.Sub,
            ast.Mult: self.viper_ast.Mul,
            ast.Div: self.viper_ast.Div,  # Note that / in Vyper means floor division
            ast.Mod: self.viper_ast.Mod,
            ast.Eq: self.viper_ast.EqCmp,
            ast.NotEq: self.viper_ast.NeCmp,
            ast.Lt: self.viper_ast.LtCmp,
            ast.LtE: self.viper_ast.LeCmp,
            ast.Gt: self.viper_ast.GtCmp,
            ast.GtE: self.viper_ast.GeCmp,
            ast.And: self.viper_ast.And,
            ast.Or: self.viper_ast.Or,
            ast.Not: self.viper_ast.Not
        }

    def translate_Num(self, node: ast.Num, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node)
        info = self.no_info()

        if isinstance(node.n, int):
            lit = self.viper_ast.IntLit(node.n, pos, info)
            return [], lit
        elif isinstance(node.n, float):
            raise UnsupportedException(node, "Float not yet supported")
        else:
            raise UnsupportedException(node, 'Unsupported number literal')

    def translate_NameConstant(self, node: ast.NameConstant, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node)
        info = self.no_info()

        if node.value is True:
            return [], self.viper_ast.TrueLit(pos, info)
        elif node.value is False:
            return [], self.viper_ast.FalseLit(pos, info)
        elif node.value is None:
            # TODO: assign 0 if value
            return [], self.viper_ast.NullLit(pos, info)
        else:
            raise UnsupportedException(node)

    def translate_Name(self, node: ast.Name, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node)
        info = self.no_info()

        return [], ctx.all_vars[node.id].localVar()

    def translate_BinOp(self, node: ast.BinOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node)
        info = self.no_info()

        left_stmt, left = self.translate(node.left, ctx)
        right_stmt, right = self.translate(node.right, ctx)
        stmt = left_stmt + right_stmt
        
        op = self.translate_operator(node.op)

        return stmt, op(left, right, pos, info)

    def translate_BoolOp(self, node: ast.BoolOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node)
        info = self.no_info()

        op = self.translate_operator(node.op)

        def build(values):
            head, *tail = values
            stmts, lhs = self.translate(head, ctx)
            if (len(tail) == 0):
                return stmts, lhs
            else:
                more, rhs = build(tail)
                return stmts + more, op(lhs, rhs, pos, info)
            
        return build(node.values)

    def translate_UnaryOp(self, node: ast.UnaryOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node)
        info = self.no_info()

        op = self.translate_operator(node.op)

        stmts, expr = self.translate(node.operand, ctx)
        return stmts, op(expr, pos, info)

    def translate_Compare(self, node: ast.Compare, ctx: Context) -> StmtsAndExpr:
        # TODO: treat in and not in differently
        pos = self.to_position(node)
        info = self.no_info()

        lhs_stmts, lhs = self.translate(node.left, ctx)
        op = self.translate_operator(node.ops[0])
        rhs_stmts, rhs = self.translate(node.comparators[0], ctx)

        return lhs_stmts + rhs_stmts, op(lhs, rhs, pos, info)

    def translate_operator(self, operator):
        return self._operations[type(operator)]

    def translate_Call(self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node)
        info = self.no_info()

        if isinstance(node.func, ast.Name):
            is_min = node.func.id == 'min'
            is_max = node.func.id == 'max'
            if is_min or is_max:
                lhs_stmts, lhs = self.translate(node.args[0], ctx)
                rhs_stmts, rhs = self.translate(node.args[1], ctx)
                op = self.viper_ast.GtCmp if is_max else self.viper_ast.LtCmp
                comp = op(lhs, rhs, pos, info) 
                stmts = lhs_stmts + rhs_stmts
                return stmts, self.viper_ast.CondExp(comp, lhs, rhs, pos, info)
        
        # TODO: error handling
        raise AssertionError("Not yet supported")
                

