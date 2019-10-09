"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from contextlib import contextmanager

from nagini_translation.utils import first_index, NodeVisitor, switch

from nagini_translation.ast import names
from nagini_translation.ast import types
from nagini_translation.ast.types import TypeBuilder, MapType, ArrayType
from nagini_translation.ast.nodes import VyperProgram

from nagini_translation.exceptions import InvalidProgramException, UnsupportedException


class TypeAnnotator(NodeVisitor):

    # The type annotator annotates all expression nodes with type information.
    # It works by using the visitor pattern as follows:
    # - Each expression that is visited returns a list of possible types for it (ordered by
    #   priority) and a list of nodes which will have that type, e.g., the literal 5 will return
    #   the types [int128, uint256, address] when visited, and itself as the only node.
    # - Statements simply return None, as they don't have types.
    # - Some operations, e.g., binary operations, have as their result type the same type
    #   as the input type. The 'combine' method combines the input type sets for that.
    # - If the required type is known at some point, 'annotate_expected' can be called with
    #   the expected type as the argument. It then checks that the nodes of the expected type
    #   and annotates all nodes.
    # - If any type can be used, 'annotate' can be called to annotate all nodes with the first
    #   type in the list, i.e., the type with the highest priority.

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

    @contextmanager
    def _function_scope(self, func):
        old_func = self.current_func
        self.current_func = func

        yield

        self.current_func = old_func

    @contextmanager
    def _quantified_vars_scope(self):
        old_quantified_vars = self.quantified_vars.copy()

        yield

        self.quantified_vars = old_quantified_vars

    @property
    def method_name(self):
        return 'visit'

    def annotate_program(self):
        for function in self.program.functions.values():
            with self._function_scope(function):
                self.visit(function.node)
                for post in function.postconditions:
                    self.annotate_expected(post, types.VYPER_BOOL)
                for check in function.checks:
                    self.annotate_expected(check, types.VYPER_BOOL)

        for inv in self.program.invariants:
            self.annotate_expected(inv, types.VYPER_BOOL)

        for post in self.program.general_postconditions:
            self.annotate_expected(post, types.VYPER_BOOL)

        for post in self.program.transitive_postconditions:
            self.annotate_expected(post, types.VYPER_BOOL)

        for check in self.program.general_checks:
            self.annotate_expected(check, types.VYPER_BOOL)

    def generic_visit(self, node: ast.AST):
        assert False

    def pass_through(self, node1, node=None):
        types, nodes = self.visit(node1)
        if node is not None:
            nodes.append(node)
        return types, nodes

    def combine(self, node1, node2, node=None):
        types1, nodes1 = self.visit(node1)
        types2, nodes2 = self.visit(node2)

        def is_array(t):
            return isinstance(t, ArrayType) and not t.is_strict

        def longest_array(matching, lst):
            try:
                arrays = [t for t in lst if is_array(t) and t.element_type == matching.element_type]
                return max(arrays, key=lambda t: t.size)
            except ValueError:
                raise InvalidProgramException(matching, 'invalid.type')

        def intersect(l1, l2):
            for e in l1:
                if is_array(e):
                    yield longest_array(e, l2)
                elif any(types.matches(t, e) and types.matches(e, t) for t in l2):
                    yield e

        intersection = list(intersect(types1, types2))
        if not intersection:
            raise InvalidProgramException(node if node is not None else node2, 'invalid.type')
        else:
            if node:
                return intersection, [*nodes1, *nodes2, node]
            else:
                return intersection, [*nodes1, *nodes2]

    def annotate(self, node1, node2=None):
        if node2 is None:
            combined, nodes = self.visit(node1)
        else:
            combined, nodes = self.combine(node1, node2)
        for node in nodes:
            node.type = combined[0]

    def annotate_expected(self, node, expected_type=None, pred=None):
        tps, nodes = self.visit(node)

        def annotate_nodes(t):
            node.type = t
            for n in nodes:
                n.type = t

        if expected_type is not None and any(types.matches(t, expected_type) for t in tps):
            annotate_nodes(expected_type)
            return
        elif pred:
            for t in tps:
                if pred(t):
                    annotate_nodes(t)
                    return

        raise InvalidProgramException(node, 'invalid.type')

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for stmt in node.body:
            self.visit(stmt)

    def visit_Return(self, node: ast.Return):
        if node.value:
            self.annotate_expected(node.value, self.current_func.type.return_type)

    def visit_Assign(self, node: ast.Assign):
        self.annotate(node.targets[0], node.value)

    def visit_AugAssign(self, node: ast.AugAssign):
        self.annotate(node.target, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if node.value:
            self.annotate(node.target, node.value)
        else:
            self.annotate(node.target)

    def visit_For(self, node: ast.For):
        self.annotate(node.iter)
        self.annotate(node.target)
        for stmt in node.body + node.orelse:
            self.visit(stmt)

    def visit_If(self, node: ast.If):
        self.annotate_expected(node.test, types.VYPER_BOOL)
        for stmt in node.body + node.orelse:
            self.visit(stmt)

    def visit_Raise(self, node: ast.Raise):
        if not (isinstance(node.exc, ast.Name) and node.exc.id == names.UNREACHABLE):
            self.annotate(node.exc)

    def visit_Assert(self, node: ast.Assert):
        self.annotate_expected(node.test, types.VYPER_BOOL)

    def visit_Expr(self, node: ast.Expr):
        self.annotate(node.value)

    def visit_Pass(self, node: ast.Pass):
        pass

    def visit_Continue(self, node: ast.Continue):
        pass

    def visit_Break(self, node: ast.Break):
        pass

    def visit_BoolOp(self, node: ast.BoolOp):
        for value in node.values:
            self.annotate_expected(value, types.VYPER_BOOL)
        return [types.VYPER_BOOL], [node]

    def visit_BinOp(self, node: ast.BinOp):
        return self.combine(node.left, node.right, node)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        return self.pass_through(node.operand, node)

    def visit_IfExp(self, node: ast.IfExp):
        self.annotate_expected(node.test, types.VYPER_BOOL)
        return self.combine(node.body, node.orelse, node)

    def visit_Compare(self, node: ast.Compare):
        self.annotate(node.left, node.comparators[0])
        return [types.VYPER_BOOL], [node]

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            name = node.func.id

            # TODO: check correct number of arguments

            with switch(name) as case:
                if case(names.CONVERT):
                    self.annotate(node.args[0])
                    ntype = self.type_builder.build(node.args[1])
                    return [ntype], [node]
                elif case(names.SUCCESS):
                    return [types.VYPER_BOOL], [node]
                elif case(names.FORALL):
                    return self._visit_forall(node)
                elif case(names.ACCESSIBLE):
                    return self._visit_accessible(node)
                elif case(names.EVENT):
                    return self._visit_event(node)
                elif case(names.MIN) or case(names.MAX):
                    self.annotate_expected(node.args[0], pred=types.is_numeric)
                    self.annotate_expected(node.args[1], pred=types.is_numeric)
                    return self.combine(node.args[0], node.args[1], node)
                elif case(names.OLD) or case(names.ISSUED):
                    return self.pass_through(node.args[0], node)
                elif case(names.REORDER_INDEPENDENT):
                    self.annotate(node.args[0])
                    return [types.VYPER_BOOL], [node]
                elif case(names.FLOOR) or case(names.CEIL):
                    self.annotate_expected(node.args[0], types.VYPER_DECIMAL)
                    return [types.VYPER_INT128], [node]
                elif case(names.RANGE):
                    self.annotate_expected(node.args[0], pred=types.is_integer)
                    return [None], [node]
                elif case(names.LEN):
                    self.annotate_expected(node.args[0], pred=lambda t: isinstance(t, types.ArrayType))
                    return [types.VYPER_INT128], [node]
                elif case(names.SEND):
                    self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                    self.annotate_expected(node.args[1], types.VYPER_WEI_VALUE)
                    return [None], [node]
                elif case(names.CLEAR):
                    # Not type checking is needed here as clear may only occur in actual Vyper code
                    self.annotate(node.args[0])
                    return [None], [node]
                elif case(names.RAW_CALL):
                    # No type checking is needed here as raw_call may only occur in actual Vyper code
                    for arg in node.args:
                        self.annotate(arg)
                    for kwarg in node.keywords:
                        self.annotate(kwarg.value)

                    idx = first_index(lambda n: n.arg == names.RAW_CALL_OUTSIZE, node.keywords)
                    size = node.keywords[idx].value.n
                    return [ArrayType(types.VYPER_BYTE, size, False)], [node]
                elif case(names.AS_WEI_VALUE):
                    self.annotate_expected(node.args[0], pred=types.is_integer)
                    # TODO: second part is string literal
                    return [types.VYPER_WEI_VALUE], [node]
                elif case(names.AS_UNITLESS_NUMBER):
                    # We ignore units completely, therefore the type stays the same
                    return self.pass_through(node.args[0], node)
                elif case(names.CONCAT):

                    def is_bytes_array(t):
                        return isinstance(t, types.ArrayType) and t.element_type == types.VYPER_BYTE

                    for arg in node.args:
                        self.annotate_expected(arg, pred=is_bytes_array)

                    size = sum(arg.type.size for arg in node.args)
                    return [ArrayType(node.args[0].type.element_type, size, False)], [node]
                elif case(names.KECCAK256) or case(names.SHA256):

                    def is_bytes_array(t):
                        return isinstance(t, types.ArrayType) and t.element_type == types.VYPER_BYTE

                    self.annotate_expected(node.args[0], pred=is_bytes_array)
                    return [types.VYPER_BYTES32], [node]
                elif case(names.IMPLIES):
                    self.annotate_expected(node.args[0], types.VYPER_BOOL)
                    self.annotate_expected(node.args[1], types.VYPER_BOOL)
                    return [types.VYPER_BOOL], [node]
                elif case(names.RESULT):
                    return [self.current_func.type.return_type], [node]
                elif case(names.SUM):

                    def is_numeric_map(t):
                        return isinstance(t, types.MapType) and types.is_integer(t.value_type)

                    self.annotate_expected(node.args[0], pred=is_numeric_map)
                    return [node.args[0].type.value_type], [node]
                elif case(names.SENT) or case(names.RECEIVED):
                    if not node.args:
                        type = types.MapType(types.VYPER_ADDRESS, types.VYPER_WEI_VALUE)
                        return [type], [node]
                    else:
                        self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                        return [types.VYPER_WEI_VALUE], [node]
                elif len(node.args) == 1 and isinstance(node.args[0], ast.Dict):
                    # This is a struct inizializer
                    return self._visit_struct_init(node)
                elif name in self.program.contracts:
                    # This is a contract initializer
                    self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                    return [self.program.contracts[name].type], [node]
                else:
                    raise UnsupportedException(node, "Unsupported function call")
        elif isinstance(node.func, ast.Attribute):
            self.annotate(node.func.value)
            receiver_type = node.func.value.type

            # We don't have to type check calls as they are not allowed in specifications
            for arg in node.args:
                self.annotate(arg)

            for kw in node.keywords:
                self.annotate(kw.value)

            # A logging call
            if not receiver_type:
                return [None], [node]

            # A self call
            if isinstance(receiver_type, types.StructType):
                name = node.func.attr
                function = self.program.functions[name]
                return [function.type.return_type], [node]
            # A contract call
            elif isinstance(receiver_type, types.ContractType):
                name = node.func.attr
                return [receiver_type.function_types[name].return_type], [node]
        else:
            assert False

    def _visit_forall(self, node: ast.Call):
        with self._quantified_vars_scope():
            var_decls = node.args[0]  # This is a dictionary of variable declarations
            vars_types = zip(var_decls.keys, var_decls.values)
            for name, type_ann in vars_types:
                type = self.type_builder.build(type_ann)
                self.quantified_vars[name.id] = type
                name.type = type

            for arg in node.args[1:len(node.args) - 1]:
                self.annotate(arg)

            # The quantified expression is always a Boolean
            self.annotate_expected(node.args[len(node.args) - 1], types.VYPER_BOOL)

        return [types.VYPER_BOOL], [node]

    def _visit_accessible(self, node: ast.Call):
        self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
        self.annotate_expected(node.args[1], types.VYPER_WEI_VALUE)
        if len(node.args) == 3:
            function = self.program.functions[node.args[2].func.attr]
            for arg, type in zip(node.args[2].args, function.type.arg_types):
                self.annotate_expected(arg, type)
        return [types.VYPER_BOOL], [node]

    def _visit_event(self, node: ast.Call):
        event_name = node.args[0].func.id
        event_type = self.program.events[event_name].type

        for arg, type in zip(node.args[0].args, event_type.arg_types):
            self.annotate_expected(arg, type)

        if len(node.args) == 2:
            self.annotate_expected(node.args[1], types.VYPER_UINT256)

        return [types.VYPER_BOOL], [node]

    def _visit_struct_init(self, node: ast.Call):
        ntype = self.program.structs[node.func.id].type

        for key, value in zip(node.args[0].keys, node.args[0].values):
            type = ntype.member_types[key.id]
            self.annotate_expected(value, type)

        return [ntype], [node]

    def visit_Bytes(self, node: ast.Bytes):
        ntype = types.ArrayType(types.VYPER_BYTE, len(node.s), False)
        return [ntype], [node]

    def visit_Str(self, node: ast.Str):
        string_bytes = bytes(node.s, 'utf-8')
        ntype = types.StringType(len(string_bytes))
        return [ntype], [node]

    # Sets occur in trigger expressions
    def visit_Set(self, node: ast.Set):
        for elem in node.elts:
            self.annotate(elem)
        return [None], [node]

    def visit_Num(self, node: ast.Num):
        if isinstance(node.n, int):
            if node.n >= 0:
                tps = [types.VYPER_INT128,
                       types.VYPER_UINT256,
                       types.VYPER_ADDRESS]
            else:
                tps = [types.VYPER_INT128]
            nodes = [node]
            return tps, nodes
        elif isinstance(node.n, float):
            return [types.VYPER_DECIMAL], [node]
        else:
            assert False

    def visit_NameConstant(self, node: ast.NameConstant):
        assert node.value is not None
        return [types.VYPER_BOOL], [node]

    def visit_Attribute(self, node: ast.Attribute):
        self.annotate(node.value)
        ntype = node.value.type.member_types[node.attr]
        return [ntype], [node]

    def visit_Subscript(self, node: ast.Subscript):
        self.annotate(node.value)
        if isinstance(node.value.type, MapType):
            key_type = node.value.type.key_type
            self.annotate_expected(node.slice.value, key_type)
            ntype = node.value.type.value_type
        elif isinstance(node.value.type, ArrayType):
            self.annotate_expected(node.slice.value, pred=types.is_integer)
            ntype = node.value.type.element_type
        else:
            assert False

        return [ntype], [node]

    def visit_Name(self, node: ast.Name):
        # TODO: replace by type map
        if node.id == names.SELF:
            ntype = self.program.fields.type
        elif node.id == names.BLOCK:
            ntype = types.BLOCK_TYPE
        elif node.id == names.MSG:
            ntype = types.MSG_TYPE
        elif node.id == names.TX:
            ntype = types.TX_TYPE
        elif node.id == names.LOG:
            ntype = None
        else:
            quant = self.quantified_vars.get(node.id)
            if quant:
                ntype = quant
            else:
                local = self.current_func.local_vars.get(node.id)
                arg = self.current_func.args.get(node.id)
                ntype = (arg or local).type
        return [ntype], [node]

    def visit_List(self, node: ast.List):
        # Vyper guarantees that size > 0
        size = len(node.elts)
        for e in node.elts:
            self.annotate(e)
        element_types = [e.type for e in node.elts]
        for element_type in element_types:
            if element_type != types.VYPER_INT128:
                return [types.ArrayType(element_type, size)], [node]
        else:
            return [types.ArrayType(types.VYPER_INT128, size)], [node]
