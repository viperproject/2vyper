"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.utils import first_index

from nagini_translation.ast import names
from nagini_translation.ast import types
from nagini_translation.ast.types import TypeBuilder, MapType, ArrayType
from nagini_translation.ast.nodes import VyperProgram

from nagini_translation.exceptions import UnsupportedException


class TypeAnnotator:

    def __init__(self, program: VyperProgram):
        type_map = {}
        for name, struct in program.structs.items():
            type_map[name] = struct.type
        for name, contract in program.contracts.items():
            type_map[name] = contract.type

        self.type_builder = TypeBuilder(type_map)

        self.program = program
        self.current_func = None
        self.quantified_vars = {}

    def annotate_program(self):
        for function in self.program.functions.values():
            self.current_func = function
            self.annotate(function.node)
            for post in function.postconditions:
                self.annotate(post)
            for check in function.checks:
                self.annotate(check)
            self.current_func = None

        for inv in self.program.invariants:
            self.annotate(inv)

        for post in self.program.general_postconditions:
            self.annotate(post)

        for check in self.program.general_checks:
            self.annotate(check)

    def annotate(self, node: ast.AST):
        """Annotate a node."""
        method = 'annotate_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_annotate)
        return visitor(node)

    def generic_annotate(self, node: ast.AST):
        assert False

    def annotate_FunctionDef(self, node: ast.FunctionDef):
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

    def annotate_Raise(self, node: ast.Raise):
        if not (isinstance(node.exc, ast.Name) and node.exc.id == names.UNREACHABLE):
            self.annotate(node.exc)

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

    def annotate_IfExp(self, node: ast.IfExp):
        self.annotate(node.test)
        self.annotate(node.body)
        self.annotate(node.orelse)
        node.type = node.body.type

    def annotate_Compare(self, node: ast.Compare):
        node.type = types.VYPER_BOOL
        self.annotate(node.left)
        self.annotate(node.comparators[0])

    def annotate_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id == names.CONVERT:
                self.annotate(node.args[0])
                node.type = self.type_builder.build(node.args[1])
                return
            elif node.func.id == names.SUCCESS:
                node.type = types.VYPER_BOOL
                return
            elif node.func.id == names.FORALL:
                self._annotate_forall(node)
                return
            elif node.func.id == names.ACCESSIBLE:
                self._annotate_accessible(node)
                return
            elif node.func.id == names.EVENT:
                self._annotate_event(node)
                return
            # struct initializers have a single argument that is a map from members
            # to values
            elif len(node.args) == 1 and isinstance(node.args[0], ast.Dict):
                self._annotate_struct_init(node)
                return

        for arg in node.args:
            self.annotate(arg)

        for key in node.keywords:
            self.annotate(key.value)

        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name == names.MIN or name == names.MAX or name == names.OLD or name == names.ISSUED:
                node.type = node.args[0].type
            elif name == names.FLOOR or name == names.CEIL or name == names.RANGE or name == names.LEN:
                node.type = types.VYPER_INT128
            elif name == names.CLEAR or name == names.SEND:
                node.type = None
            elif name == names.RAW_CALL:
                idx = first_index(lambda n: n.arg == names.RAW_CALL_OUTSIZE, node.keywords)
                size = node.keywords[idx].value.n
                node.type = ArrayType(types.VYPER_BYTE, size, False)
            elif name == names.AS_WEI_VALUE:
                node.type = types.VYPER_WEI_VALUE
            elif name == names.AS_UNITLESS_NUMBER:
                # For now the only unit supported is wei_value which is an uint256
                node.type = types.VYPER_WEI_VALUE
            elif name == names.CONCAT:
                size = sum(arg.type.size for arg in node.args)
                node.type = ArrayType(node.args[0].type.element_type, size, False)
            elif name == names.KECCAK256 or name == names.SHA256:
                node.type = types.VYPER_BYTES32
            elif name == names.IMPLIES:
                node.type = types.VYPER_BOOL
            elif name == names.RESULT:
                node.type = self.current_func.type.return_type
            elif name == names.SUM:
                node.type = node.args[0].type.value_type
            elif name == names.SENT or name == names.RECEIVED:
                if not node.args:
                    node.type = types.MapType(types.VYPER_ADDRESS, types.VYPER_WEI_VALUE)
                else:
                    node.type = types.VYPER_WEI_VALUE
            elif name in self.program.contracts:
                # This is a contract initializer
                node.type = self.program.contracts[name].type
            else:
                raise UnsupportedException(node, "Unsupported function call")
        elif isinstance(node.func, ast.Attribute):
            self.annotate(node.func.value)
            receiver_type = node.func.value.type
            # A logging call
            if not receiver_type:
                node.type = None
            # A self call
            elif isinstance(receiver_type, types.StructType):
                name = node.func.attr
                function = self.program.functions[name]
                node.type = function.type.return_type
            # A contract call
            elif isinstance(receiver_type, types.ContractType):
                name = node.func.attr
                node.type = receiver_type.function_types[name].return_type
        else:
            assert False

    def _annotate_forall(self, node: ast.Call):
        node.type = types.VYPER_BOOL

        old_quants = self.quantified_vars.copy()
        var_decls = node.args[0]  # This is a dictionary of variable declarations
        vars_types = zip(var_decls.keys, var_decls.values)
        for name, type_ann in vars_types:
            type = self.type_builder.build(type_ann)
            self.quantified_vars[name.id] = type
            name.type = type

        for arg in node.args[1:]:
            self.annotate(arg)

        self.quantified_vars = old_quants

    def _annotate_accessible(self, node: ast.Call):
        self.annotate(node.args[0])
        self.annotate(node.args[1])
        if len(node.args) == 3:
            for arg in node.args[2].args:
                self.annotate(arg)

    def _annotate_event(self, node: ast.Call):
        for arg in node.args[0].args:
            self.annotate(arg)

        if len(node.args) == 2:
            self.annotate(node.args[1])

        node.type = types.VYPER_BOOL

    def _annotate_struct_init(self, node: ast.Call):
        node.type = self.program.structs[node.func.id].type
        for value in node.args[0].values:
            self.annotate(value)

    def annotate_Bytes(self, node: ast.Bytes):
        node.type = types.ArrayType(types.VYPER_BYTE, len(node.s), False)

    def annotate_Str(self, node: ast.Str):
        string_bytes = bytes(node.s, 'utf-8')
        node.type = types.StringType(len(string_bytes))

    def annotate_Set(self, node: ast.Set):
        for elem in node.elts:
            self.annotate(elem)

    def annotate_Num(self, node: ast.Num):
        if isinstance(node.n, int):
            node.type = types.VYPER_INT128
        elif isinstance(node.n, float):
            node.type = types.VYPER_DECIMAL
        else:
            assert False

    def annotate_NameConstant(self, node: ast.NameConstant):
        assert node.value is not None
        node.type = types.VYPER_BOOL

    def annotate_Attribute(self, node: ast.Attribute):
        self.annotate(node.value)
        node.type = node.value.type.member_types[node.attr]

    def annotate_Subscript(self, node: ast.Subscript):
        self.annotate(node.value)
        if isinstance(node.value.type, MapType):
            self.annotate(node.slice.value)
            node.type = node.value.type.value_type
        elif isinstance(node.value.type, ArrayType):
            self.annotate(node.slice.value)
            node.type = node.value.type.element_type
        else:
            assert False

    def annotate_Name(self, node: ast.Name):
        # TODO: replace by type map
        if node.id == names.SELF:
            node.type = self.program.fields.type
        elif node.id == names.BLOCK:
            node.type = types.BLOCK_TYPE
        elif node.id == names.MSG:
            node.type = types.MSG_TYPE
        elif node.id == names.LOG:
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
