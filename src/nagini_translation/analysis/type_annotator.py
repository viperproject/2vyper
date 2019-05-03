"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.ast import names
from nagini_translation.ast import types
from nagini_translation.ast.types import VyperType
from nagini_translation.ast.nodes import VyperProgram


class TypeAnnotator:

    # TODO: error handling

    def __init__(self, program: VyperProgram):
        self.program = program
        self.current_func = None

    def annotate_program(self):
        for function in self.program.functions.values():
            self.current_func = function
            self.annotate(function.node, None)
            for pre in function.preconditions:
                self.annotate(pre, types.VYPER_BOOL)
            for post in function.postconditions:
                self.annotate(post, types.VYPER_BOOL)
            self.current_func = None
        
        for inv in self.program.invariants:
            self.annotate(inv, types.VYPER_BOOL)

    def annotate(self, node: ast.AST, expected: VyperType):
        """Annotate a node."""
        method = 'annotate_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_annotate)
        return visitor(node, expected)

    def generic_annotate(self, node: ast.AST, expected: VyperType):
        assert False

    def annotate_FunctionDef(self, node: ast.FunctionDef, expected: VyperType):
        ret_type = self.program.functions[node.name].ret

        for stmt in node.body:
            self.annotate(stmt, ret_type)

    def annotate_Return(self, node: ast.Return, expected: VyperType):
        if node.value:
            self.annotate(node.value, expected)

    def annotate_Assign(self, node: ast.Assign, expected: VyperType):
        self.annotate(node.targets[0], None)
        self.annotate(node.value, node.targets[0].type)

    def annotate_AugAssign(self, node: ast.AugAssign, expected: VyperType):
        self.annotate(node.target, None)
        self.annotate(node.value, node.target.type)

    def annotate_AnnAssign(self, node: ast.AnnAssign, expected: VyperType):
        self.annotate(node.target, None)
        if node.value:
            self.annotate(node.value, node.target)
    
    def annotate_For(self, node: ast.For, expected: VyperType):
        self.annotate(node.iter, None)
        self.annotate(node.target, node.iter.type)
        for stmt in node.body + node.orelse:
            self.annotate(stmt, expected)

    def annotate_If(self, node: ast.If, expected: VyperType):
        self.annotate(node.test, types.VYPER_BOOL)
        for stmt in node.body + node.orelse:
            self.annotate(stmt, expected)

    def annotate_Assert(self, node: ast.Assert, expected: VyperType):
        self.annotate(node.test, types.VYPER_BOOL)

    def annotate_Pass(self, node: ast.Pass, expected: VyperType):
        pass

    def annotate_Continue(self, node: ast.Continue, expected: VyperType):
        pass

    def annotate_Break(self, node: ast.Break, expected: VyperType):
        pass
    
    def annotate_BoolOp(self, node: ast.BoolOp, expected: VyperType):
        node.type = types.VYPER_BOOL
        for value in node.values:
            self.annotate(value, types.VYPER_BOOL)

    def annotate_BinOp(self, node: ast.BinOp, expected: VyperType):
        self.annotate(node.left, expected)
        self.annotate(node.right, expected)
        if node.left.type == types.VYPER_INT128:
            node.type = node.right.type
        else:
            node.type = node.left.type

    def annotate_UnaryOp(self, node: ast.UnaryOp, expected: VyperType):
        self.annotate(node.operand, expected)
        node.type = node.operand.type

    def annotate_Compare(self, node: ast.Compare, expected: VyperType):
        node.type = types.VYPER_BOOL
        self.annotate(node.left, None)
        self.annotate(node.comparators[0], None)

    def annotate_Call(self, node: ast.Call, expected: VyperType):
        for arg in node.args:
            self.annotate(arg, None)
        
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name == names.MIN or name == names.MAX or name == names.OLD or name == names.IMPLIES:
                node.type = node.args[0].type
            elif name == names.RANGE:
                node.type = types.VYPER_INT128
            elif name == names.SUCCESS:
                node.type = types.VYPER_BOOL
            elif name == names.RESULT:
                node.type = self.current_func.ret
            elif name == names.SUM:
                node.type = node.args[0].type.value_type
            else:
                assert False, f"encountered function {node.func.id}"
        else:
            assert False

    def annotate_Num(self, node: ast.Num, expected: VyperType):
        node.type = types.VYPER_INT128

    def annotate_NameConstant(self, node: ast.NameConstant, expected: VyperType):
        if node.value == True or node.value == False:
            node.type = types.VYPER_BOOL
        else:
            assert False, "encountered None"

    def annotate_Attribute(self, node: ast.Attribute, expected: VyperType):
        self.annotate(node.value, None)
        if node.attr == names.MSG_SENDER:
            node.type = types.VYPER_ADDRESS
        else:
            node.type = self.program.state[node.attr].type

    def annotate_Subscript(self, node: ast.Subscript, expected: VyperType):
        self.annotate(node.value, None)
        self.annotate(node.slice.value, node.value.type.key_type)
        node.type = node.value.type.value_type

    def annotate_Name(self, node: ast.Name, expected: VyperType):
        if node.id == names.SELF or node.id == names.MSG:
            node.type = None
        else:
            local = self.current_func.local_vars.get(node.id)
            arg = self.current_func.args.get(node.id)
            node.type = (arg or local or expected).type

