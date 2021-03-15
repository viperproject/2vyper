"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Dict, Any, Tuple

from twovyper.ast import ast_nodes as ast, names
from twovyper.ast.arithmetic import div, mod, Decimal
from twovyper.ast.visitors import NodeVisitor, NodeTransformer, descendants

from twovyper.exceptions import UnsupportedException

from twovyper.parsing import lark
from twovyper.utils import switch


def transform(vyper_ast: ast.Module) -> ast.Module:
    constants_decls, new_ast = ConstantCollector().collect_constants(vyper_ast)
    constant_values, constant_nodes = _interpret_constants(constants_decls)
    transformed_ast = ConstantTransformer(constant_values, constant_nodes).visit(new_ast)
    return transformed_ast


def _parse_value(val) -> ast.Expr:
    """
    Returns a new ast.Node containing the value.
    """
    return lark.parse_expr(f'{val}', None)


def _builtin_constants():
    values = {name: value for name, value in names.CONSTANT_VALUES.items()}
    constants = {name: _parse_value(value) for name, value in names.CONSTANT_VALUES.items()}
    return values, constants


def _interpret_constants(nodes: List[ast.AnnAssign]) -> Tuple[Dict[str, Any], Dict[str, ast.Node]]:
    env, constants = _builtin_constants()
    interpreter = ConstantInterpreter(env)
    for node in nodes:
        name = node.target.id
        value = interpreter.visit(node.value)
        env[name] = value
        constants[name] = _parse_value(value)

    return env, constants


class ConstantInterpreter(NodeVisitor):
    """
    Determines the value of all constants in the AST.
    """

    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants

    def generic_visit(self, node: ast.Node, *args):
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

        with switch(node.op) as case:
            if case(ast.ComparisonOperator.LT):
                return lhs < rhs
            elif case(ast.ComparisonOperator.LTE):
                return lhs <= rhs
            elif case(ast.ComparisonOperator.GT):
                return lhs > rhs
            elif case(ast.ComparisonOperator.GTE):
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
        elif node.name == names.CONVERT:
            arg = args[0]
            second_arg = node.args[1]
            assert isinstance(second_arg, ast.Name)
            type_name = second_arg.id
            if isinstance(arg, int):
                with switch(type_name) as case:
                    if case(names.BOOL):
                        return bool(arg)
                    elif case(names.DECIMAL):
                        return Decimal[10](value=arg)
                    elif (case(names.INT128)
                          or case(names.UINT256)
                          or case(names.BYTES32)):
                        return arg
            elif isinstance(arg, Decimal):
                with switch(type_name) as case:
                    if case(names.BOOL):
                        # noinspection PyUnresolvedReferences
                        return bool(arg.scaled_value)
                    elif case(names.DECIMAL):
                        return arg
                    elif (case(names.INT128)
                          or case(names.UINT256)
                          or case(names.BYTES32)):
                        # noinspection PyUnresolvedReferences
                        return div(arg.scaled_value, arg.scaling_factor)
            elif isinstance(arg, bool):
                with switch(type_name) as case:
                    if case(names.BOOL):
                        return arg
                    elif (case(names.DECIMAL)
                          or case(names.INT128)
                          or case(names.UINT256)
                          or case(names.BYTES32)):
                        return int(arg)

        raise UnsupportedException(node)

    @staticmethod
    def visit_Num(node: ast.Num):
        if isinstance(node.n, int) or isinstance(node.n, Decimal):
            return node.n
        else:
            assert False

    @staticmethod
    def visit_Bool(node: ast.Bool):
        return node.value

    def visit_Str(self, node: ast.Str):
        return '"{}"'.format(node.s)

    def visit_Name(self, node: ast.Name):
        return self.constants.get(node.id)

    def visit_List(self, node: ast.List):
        return [self.visit(element) for element in node.elements]


class ConstantCollector(NodeTransformer):
    """
    Collects constants and deletes their declarations from the AST.
    """

    def __init__(self):
        self.constants = []

    @staticmethod
    def _is_constant(node: ast.Node):
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

    @staticmethod
    def visit_FunctionDef(node: ast.FunctionDef):
        return node


class ConstantTransformer(NodeTransformer):
    """
    Replaces all constants in the AST by their value.
    """

    def __init__(self, constant_values: Dict[str, Any], constant_nodes: Dict[str, ast.Node]):
        self.constants = constant_nodes
        self.interpreter = ConstantInterpreter(constant_values)

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

    # noinspection PyBroadException
    def visit_FunctionCall(self, node: ast.FunctionCall):
        if node.name == names.RANGE:
            if len(node.args) == 1:
                try:
                    val = self.interpreter.visit(node.args[0])
                    new_node = _parse_value(val)
                    new_node = self._copy_pos(new_node, node.args[0])
                    assert isinstance(new_node, ast.Expr)
                    node.args[0] = new_node
                except Exception:
                    pass
            elif len(node.args) == 2:
                first_arg = node.args[0]
                second_arg = node.args[1]
                if isinstance(second_arg, ast.ArithmeticOp) \
                        and second_arg.op == ast.ArithmeticOperator.ADD \
                        and ast.compare_nodes(first_arg, second_arg.left):
                    try:
                        val = self.interpreter.visit(second_arg.right)
                        new_node = _parse_value(val)
                        second_arg.right = self._copy_pos(new_node, second_arg.right)
                    except Exception:
                        pass
                else:
                    try:
                        first_val = self.interpreter.visit(first_arg)
                        first_new_node = _parse_value(first_val)
                        first_new_node = self._copy_pos(first_new_node, first_arg)
                        assert isinstance(first_new_node, ast.Expr)
                        second_val = self.interpreter.visit(second_arg)
                        second_new_node = _parse_value(second_val)
                        second_new_node = self._copy_pos(second_new_node, first_arg)
                        assert isinstance(second_new_node, ast.Expr)
                        node.args[0] = first_new_node
                        node.args[1] = second_new_node
                    except Exception:
                        pass

        else:
            self.generic_visit(node)
        return node
