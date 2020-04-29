"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Dict, Any

from twovyper.ast import ast_nodes as ast, names
from twovyper.ast.arithmetic import div, mod, Decimal
from twovyper.ast.visitors import NodeVisitor, NodeTransformer, descendants

from twovyper.exceptions import UnsupportedException

from twovyper.parsing import lark


def transform(ast: ast.Module) -> ast.Module:
    constants_decls, new_ast = ConstantCollector().collect_constants(ast)
    constants = _interpret_constants(constants_decls)
    transformed_ast = ConstantTransformer(constants).visit(new_ast)
    return transformed_ast


def _parse_value(val):
    return lark.parse_expr(f'{val}', None)


def _builtin_constants():
    values = {name: value for name, value in names.CONSTANT_VALUES.items()}
    constants = {name: _parse_value(value) for name, value in names.CONSTANT_VALUES.items()}
    return values, constants


def _interpret_constants(nodes: List[ast.AnnAssign]) -> Dict[str, ast.Node]:
    env, constants = _builtin_constants()
    interpreter = ConstantInterpreter(env)
    for node in nodes:
        name = node.target.id
        value = interpreter.visit(node.value)
        env[name] = value
        constants[name] = _parse_value(value)

    return constants


class ConstantInterpreter(NodeVisitor):
    """
    Determines the value of all constants in the AST.
    """

    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants

    def generic_visit(self, node: ast.Node):
        raise UnsupportedException(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if node.op == ast.BoolOperator.AND:
            return left and right
        elif node.op == ast.BoolOperator.OR:
            return left or right
        else:
            assert False

    def visit_Not(self, node: ast.Not):
        operand = self.visit(node.operand)
        return not operand

    def visit_ArithmeticOp(self, node: ast.ArithmeticOp):
        lhs = self.visit(node.left)
        rhs = self.visit(node.right)
        op = node.op
        if op == ast.ArithmeticOperator.ADD:
            return lhs + rhs
        elif op == ast.ArithmeticOperator.SUB:
            return lhs - rhs
        elif op == ast.ArithmeticOperator.MUL:
            return lhs * rhs
        elif op == ast.ArithmeticOperator.DIV:
            return div(lhs, rhs)
        elif op == ast.ArithmeticOperator.MOD:
            return mod(lhs, rhs)
        elif op == ast.ArithmeticOperator.POW:
            return lhs ** rhs
        else:
            assert False

    def visit_UnaryArithmeticOp(self, node: ast.UnaryArithmeticOp):
        operand = self.visit(node.operand)
        if node.op == ast.UnaryArithmeticOperator.ADD:
            return operand
        elif node.op == ast.UnaryArithmeticOperator.SUB:
            return -operand
        else:
            assert False

    def visit_Comparison(self, node: ast.Comparison):
        lhs = self.visit(node.left)
        rhs = self.visit(node.right)

        if isinstance(node.op, ast.Lt):
            return lhs < rhs
        elif isinstance(node.op, ast.LtE):
            return lhs <= rhs
        elif isinstance(node.op, ast.Gt):
            return lhs > rhs
        elif isinstance(node.op, ast.GtE):
            return lhs >= rhs
        else:
            assert False

    def visit_Equality(self, node: ast.Equality):
        lhs = self.visit(node.left)
        rhs = self.visit(node.right)

        if node.op == ast.EqualityOperator.EQ:
            return lhs == rhs
        elif node.op == ast.EqualityOperator.NEQ:
            return lhs != rhs
        else:
            assert False

    def visit_FunctionCall(self, node: ast.FunctionCall):
        args = [self.visit(arg) for arg in node.args]
        if node.name == names.MIN:
            return min(args)
        elif node.name == names.MAX:
            return max(args)

        raise UnsupportedException(node)

    def visit_Num(self, node: ast.Num):
        if isinstance(node.n, int) or isinstance(node.n, Decimal):
            return node.n
        else:
            assert False

    def visit_Bool(self, node: ast.Bool):
        return node.value

    def visit_Name(self, node: ast.Name):
        return self.constants[node.id]


class ConstantCollector(NodeTransformer):
    """
    Collects constants and deletes their declarations from the AST.
    """

    def __init__(self):
        self.constants = []

    def _is_constant(self, node):
        return isinstance(node, ast.FunctionCall) and node.name == 'constant'

    def collect_constants(self, node):
        new_node = self.visit(node)
        return self.constants, new_node

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if self._is_constant(node.annotation):
            self.constants.append(node)
            return None
        else:
            return node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        return node


class ConstantTransformer(NodeTransformer):
    """
    Replaces all constants in the AST by their value.
    """

    def __init__(self, constants: Dict[str, ast.Node]):
        self.constants = constants

    def _copy_pos(self, to: ast.Node, node: ast.Node) -> ast.Node:
        to.file = node.file
        to.lineno = node.lineno
        to.col_offset = node.col_offset
        to.end_lineno = node.end_lineno
        to.end_col_offset = node.end_col_offset
        to.is_ghost_code = node.is_ghost_code
        for child in descendants(to):
            self._copy_pos(child, node)
        return to

    def visit_Name(self, node: ast.Name):
        return self._copy_pos(self.constants.get(node.id) or node, node)
