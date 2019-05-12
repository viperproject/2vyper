"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.ast import names
from nagini_translation.ast import types
from nagini_translation.ast.types import VyperType, MapType, ArrayType
from nagini_translation.ast.nodes import VyperProgram

from nagini_translation.ast.types import TypeBuilder


class TypeAnnotator:

    # TODO: error handling

    def __init__(self, program: VyperProgram):
        self.type_builder = TypeBuilder()

        self.program = program
        self.current_func = None
        self.quantified_vars = {}

    def annotate_program(self):
        for function in self.program.functions.values():
            self.current_func = function
            self.annotate(function.node)
            for pre in function.preconditions:
                self.annotate(pre)
            for post in function.postconditions:
                self.annotate(post)
            self.current_func = None

        for inv in self.program.invariants:
            self.annotate(inv)

    def annotate(self, node: ast.AST):
        """Annotate a node."""
        method = 'annotate_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_annotate)
        return visitor(node)

    def generic_annotate(self, node: ast.AST):
        assert False

    def annotate_FunctionDef(self, node: ast.FunctionDef):
        ret_type = self.program.functions[node.name].type.return_type

        for stmt in node.body:
            self.annotate(stmt)

    def annotate_Return(self, node: ast.Return):
        if node.value:
            self.annotate(node.value)

    def annotate_Assign(self, node: ast.Assign):
        self.annotate(node.targets[0])
        self.annotate(node.value)

    def annotate_AugAssign(self, node: ast.AugAssign):
        self.annotate(node.target)
        self.annotate(node.value)

    def annotate_AnnAssign(self, node: ast.AnnAssign):
        self.annotate(node.target)
        if node.value:
            self.annotate(node.value)
    
    def annotate_For(self, node: ast.For):
        self.annotate(node.iter)
        self.annotate(node.target)
        for stmt in node.body + node.orelse:
            self.annotate(stmt)

    def annotate_If(self, node: ast.If):
        self.annotate(node.test)
        for stmt in node.body + node.orelse:
            self.annotate(stmt)

    def annotate_Assert(self, node: ast.Assert):
        self.annotate(node.test)

    def annotate_Expr(self, node: ast.Expr):
        self.annotate(node.value)

    def annotate_Pass(self, node: ast.Pass):
        pass

    def annotate_Continue(self, node: ast.Continue):
        pass

    def annotate_Break(self, node: ast.Break):
        pass
    
    def annotate_BoolOp(self, node: ast.BoolOp):
        node.type = types.VYPER_BOOL
        for value in node.values:
            self.annotate(value)

    def annotate_BinOp(self, node: ast.BinOp):
        self.annotate(node.left)
        self.annotate(node.right)
        if node.left.type == types.VYPER_INT128:
            node.type = node.right.type
        else:
            node.type = node.left.type

    def annotate_UnaryOp(self, node: ast.UnaryOp):
        self.annotate(node.operand)
        node.type = node.operand.type

    def annotate_Compare(self, node: ast.Compare):
        node.type = types.VYPER_BOOL
        self.annotate(node.left)
        self.annotate(node.comparators[0])

    def annotate_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == names.FORALL:
            self._annotate_forall(node)
            return

        for arg in node.args:
            self.annotate(arg)
        
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name == names.MIN or name == names.MAX or name == names.OLD:
                node.type = node.args[0].type
            elif name == names.RANGE:
                node.type = types.VYPER_INT128
            elif name == names.CLEAR or name == names.SEND:
                node.type = None
            elif name == names.AS_WEI_VALUE:
                node.type = types.VYPER_WEI_VALUE
            elif name == names.AS_UNITLESS_NUMBER:
                # For now the only unit supported is wei_value which is an uint256
                node.type = types.VYPER_WEI_VALUE
            elif name == names.IMPLIES or name == names.SUCCESS:
                node.type = types.VYPER_BOOL
            elif name == names.RESULT:
                node.type = self.current_func.type.return_type
            elif name == names.SUM:
                node.type = node.args[0].type.value_type
            elif name == names.SENT:
                if not node.args:
                    node.type = types.MapType(types.VYPER_ADDRESS, types.VYPER_WEI_VALUE)
                else:
                    node.type = types.VYPER_WEI_VALUE
            else:
                assert False, f"encountered function {node.func.id}"
        else:
            assert False

    def annotate_Str(self, node: ast.Str):
        # Is only supported as an argument to as_wei_value
        pass

    def _annotate_forall(self, node: ast.Call):
        old_quants = self.quantified_vars.copy()
        var_decls = node.args[0] # This is a dictionary of variable declarations
        vars_types = zip(var_decls.keys, var_decls.values)
        for name, type_ann in vars_types:
            type = self.type_builder.build(type_ann)
            self.quantified_vars[name.id] = type
            name.type = type

        for arg in node.args[1:]:
            self.annotate(arg)

        self.quantified_vars = old_quants
 
    def annotate_Set(self, node: ast.Set):
        for elem in node.elts:
            self.annotate(elem)

    def annotate_Num(self, node: ast.Num):
        node.type = types.VYPER_INT128

    def annotate_NameConstant(self, node: ast.NameConstant):
        if node.value == True or node.value == False:
            node.type = types.VYPER_BOOL
        else:
            assert False, "encountered None"

    def annotate_Attribute(self, node: ast.Attribute):
        self.annotate(node.value)
        if node.attr == names.MSG_SENDER:
            node.type = types.VYPER_ADDRESS
        elif node.attr == names.MSG_VALUE or node.attr == names.SELF_BALANCE:
            node.type = types.VYPER_WEI_VALUE
        elif node.attr == names.BLOCK_TIMESTAMP:
            node.type = types.VYPER_TIME
        else:
            node.type = self.program.state[node.attr].type

    def annotate_Subscript(self, node: ast.Subscript):
        self.annotate(node.value)
        if isinstance(node.value.type, MapType):
            self.annotate(node.slice.value)
            node.type = node.value.type.value_type
        elif isinstance(node.value.type, ArrayType):
            self.annotate(node.slice.value)
            node.type = node.value.type.element_type
        else:
            assert False # TODO: handle

    def annotate_Name(self, node: ast.Name):
        if node.id == names.SELF or node.id == names.MSG or node.id == names.BLOCK:
            node.type = None
        else:
            quant = self.quantified_vars.get(node.id)
            if quant:
                node.type = quant
            else:
                local = self.current_func.local_vars.get(node.id)
                arg = self.current_func.args.get(node.id)
                node.type = (arg or local).type

    def annotate_List(self, node: ast.List):
        size = len(node.elts)
        element_types = [self.annotate(e) for e in node.elts]
        for element_type in element_types:
            if element_type != types.VYPER_INT128:
                node.type = types.ArrayType(element_type, size)
                break
        else:
            node.type = types.ArrayType(types.VYPER_INT128, size)