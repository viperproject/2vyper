"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import StmtsAndExpr

from nagini_translation.ast import names
from nagini_translation.ast import types

from nagini_translation.ast.types import MapType, ArrayType

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.context import Context
from nagini_translation.translation.builtins import map_get
from nagini_translation.translation.builtins import array_get, array_contains, array_not_contains


class ExpressionTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

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
            ast.In: lambda l, r, pos: array_contains(viper_ast, l, r, pos),
            ast.NotIn: lambda l, r, pos: array_not_contains(viper_ast, l, r, pos),
            ast.And: self.viper_ast.And,
            ast.Or: self.viper_ast.Or,
            ast.Not: self.viper_ast.Not
        }

    def translate_Num(self, node: ast.Num, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if isinstance(node.n, int):
            lit = self.viper_ast.IntLit(node.n, pos)
            return [], lit
        elif isinstance(node.n, float):
            raise UnsupportedException(node, "Float not yet supported")
        else:
            raise UnsupportedException(node, "Unsupported number literal")

    def translate_NameConstant(self, node: ast.NameConstant, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if node.value is True:
            return [], self.viper_ast.TrueLit(pos)
        elif node.value is False:
            return [], self.viper_ast.FalseLit(pos)
        else:
            raise UnsupportedException(node)

    def translate_Name(self, node: ast.Name, ctx: Context) -> StmtsAndExpr:
        return [], ctx.all_vars[node.id].localVar()

    def translate_BinOp(self, node: ast.BinOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        left_stmts, left = self.translate(node.left, ctx)
        right_stmts, right = self.translate(node.right, ctx)
        stmts = left_stmts + right_stmts
        
        op = self.translate_operator(node.op)

        def fail_if(cond):
            body = [self.viper_ast.Goto(ctx.revert_label, pos)]
            block = self.viper_ast.Seqn(body, pos)
            empty = self.viper_ast.Seqn([], pos)
            return self.viper_ast.If(cond, block, empty, pos)

        # If the divisor is 0 revert the transaction
        if isinstance(node.op, ast.Div) or isinstance(node.op, ast.Mod):
            cond = self.viper_ast.EqCmp(right, self.viper_ast.IntLit(0, pos), pos)
            stmts.append(fail_if(cond))

        # If the result of a uint subtraction is negative, revert the transaction
        if isinstance(node.op, ast.Sub) and types.is_unsigned(node.type):
            cond = self.viper_ast.GtCmp(right, left, pos)
            stmts.append(fail_if(cond))

        return stmts, op(left, right, pos)

    def translate_BoolOp(self, node: ast.BoolOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        op = self.translate_operator(node.op)

        def build(values):
            head, *tail = values
            stmts, lhs = self.translate(head, ctx)
            if (len(tail) == 0):
                return stmts, lhs
            else:
                more, rhs = build(tail)
                return stmts + more, op(lhs, rhs, pos)
            
        return build(node.values)

    def translate_UnaryOp(self, node: ast.UnaryOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        op = self.translate_operator(node.op)

        stmts, expr = self.translate(node.operand, ctx)
        return stmts, op(expr, pos)

    def translate_Compare(self, node: ast.Compare, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        lhs_stmts, lhs = self.translate(node.left, ctx)
        op = self.translate_operator(node.ops[0])
        rhs_stmts, rhs = self.translate(node.comparators[0], ctx)

        return lhs_stmts + rhs_stmts, op(lhs, rhs, pos)

    def translate_operator(self, operator):
        return self._operations[type(operator)]

    def translate_Attribute(self, node: ast.Attribute, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        stmts, expr = self.translate(node.value, ctx)
        field = ctx.fields.get(node.attr, ctx.immutable_fields.get(node.attr))
        return stmts, self.viper_ast.FieldAccess(expr, field, pos)

    def translate_Subscript(self, node: ast.Subscript, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        value_stmts, value = self.translate(node.value, ctx)
        index_stmts, index = self.translate(node.slice.value, ctx)
        stmts = []

        node_type = node.value.type
        if isinstance(node_type, MapType):
            key_type = self.type_translator.translate(node_type.key_type, ctx)
            value_type = self.type_translator.translate(node_type.value_type, ctx)
            call = map_get(self.viper_ast, value, index, key_type, value_type, pos)
        elif isinstance(node_type, ArrayType):
            stmts.append(self.type_translator.array_bounds_check(value, index, ctx))
            element_type = self.type_translator.translate(node_type.element_type, ctx)
            call = array_get(self.viper_ast, value, index, element_type, pos)

        return value_stmts + index_stmts + stmts, call

    def translate_Call(self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if isinstance(node.func, ast.Name):
            is_min = node.func.id == names.MIN
            is_max = node.func.id == names.MAX
            if is_min or is_max:
                lhs_stmts, lhs = self.translate(node.args[0], ctx)
                rhs_stmts, rhs = self.translate(node.args[1], ctx)
                op = self.viper_ast.GtCmp if is_max else self.viper_ast.LtCmp
                comp = op(lhs, rhs, pos) 
                stmts = lhs_stmts + rhs_stmts
                return stmts, self.viper_ast.CondExp(comp, lhs, rhs, pos)
        
        # TODO: error handling
        raise AssertionError("Not yet supported")
                

