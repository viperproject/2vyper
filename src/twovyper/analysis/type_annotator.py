"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from itertools import zip_longest
from contextlib import contextmanager
from typing import Optional, Union, Dict, Iterable

from twovyper.utils import first_index, switch, first

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.arithmetic import Decimal
from twovyper.ast.types import (
    TypeBuilder, VyperType, MapType, ArrayType, StringType, StructType, AnyStructType,
    SelfType, ContractType, InterfaceType, TupleType
)
from twovyper.ast.nodes import VyperProgram, VyperFunction, GhostFunction, VyperInterface
from twovyper.ast.text import pprint
from twovyper.ast.visitors import NodeVisitor

from twovyper.exceptions import InvalidProgramException, UnsupportedException
from twovyper.vyper import is_compatible_version, select_version


def _check(condition: bool, node: ast.Node, reason_code: str, msg: Optional[str] = None):
    if not condition:
        raise InvalidProgramException(node, reason_code, msg)


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
        for name, interface in program.interfaces.items():
            type_map[name] = interface.type

        self.type_builder = TypeBuilder(type_map)

        self.program = program
        self.current_func: Union[VyperFunction, None] = None
        self.current_loops: Dict[str, ast.For] = {}

        self_type = self.program.fields.type
        # Contains the possible types a variable can have
        self.known_variables = {
            names.BLOCK: [types.BLOCK_TYPE],
            names.CHAIN: [types.CHAIN_TYPE],
            names.TX: [types.TX_TYPE],
            names.MSG: [types.MSG_TYPE],
            names.SELF: [types.VYPER_ADDRESS, self_type],
            names.LOG: [None],
            names.LEMMA: [None]
        }

        self.known_variables.update({interface: [None] for interface in program.interfaces.keys()})

        self.variables = self.known_variables.copy()

        self.undecided_nodes = False
        self.type_resolver = TypeResolver()

    @contextmanager
    def _function_scope(self, func: Union[VyperFunction, GhostFunction]):
        old_func = self.current_func
        self.current_func = func
        old_variables = self.variables.copy()
        self.variables = self.known_variables.copy()
        self.variables.update({k: [v.type] for k, v in func.args.items()})

        yield

        self.current_func = old_func
        self.variables = old_variables

    @contextmanager
    def _quantified_vars_scope(self):
        old_variables = self.variables.copy()

        yield

        self.variables = old_variables

    @contextmanager
    def _loop_scope(self):
        current_loops = self.current_loops

        yield

        self.current_loops = current_loops

    @property
    def method_name(self):
        return 'visit'

    def check_number_of_arguments(self, node: Union[ast.FunctionCall, ast.ReceiverCall], *expected: int,
                                  allowed_keywords: Iterable[str] = (), required_keywords: Iterable[str] = (),
                                  resources: int = 0):
        _check(len(node.args) in expected, node, 'invalid.no.args')
        for kw in node.keywords:
            _check(kw.name in allowed_keywords, node, 'invalid.no.args')

        for kw in required_keywords:
            _check(any(k.name == kw for k in node.keywords), node, 'invalid.no.args')

        if resources > 0 and self.program.config.has_option(names.CONFIG_NO_DERIVED_WEI):
            _check(node.resource is not None, node, 'invalid.resource',
                   'The derived wei resource got disabled and cannot be used.')

        if isinstance(node, ast.FunctionCall) and node.resource:
            if resources == 1:
                cond = not isinstance(node.resource, ast.Exchange)
            elif resources == 2:
                cond = isinstance(node.resource, ast.Exchange)
            else:
                cond = False

            _check(cond, node, 'invalid.no.resources')

    def annotate_program(self):

        for resources in self.program.resources.values():
            for resource in resources:
                if (isinstance(resource.type, types.DerivedResourceType)
                        and isinstance(resource.type.underlying_resource, types.UnknownResourceType)):
                    underlying_resource, args = self._annotate_resource(resource.underlying_resource)
                    resource.underlying_address = underlying_resource.own_address
                    underlying_resource.derived_resources.append(resource)
                    if len(args) != 0:
                        _check(False, args[0], 'invalid.derived.resource',
                               'The underlying resource type must be declared without arguments.')
                    resource.type.underlying_resource = underlying_resource.type
                    derived_resource_member_types = resource.type.member_types.values()
                    underlying_resource_member_types = underlying_resource.type.member_types.values()
                    _check(resource.file != underlying_resource.file, resource.node, 'invalid.derived.resource',
                           'A resource cannot be a derived resource from a resource of the same contract.')
                    _check(resource.underlying_address is not None, resource.node, 'invalid.derived.resource',
                           'The underlying resource of a derived resource must have an address specified.')
                    for derived_member_type, underlying_member_type \
                            in zip_longest(derived_resource_member_types, underlying_resource_member_types):
                        _check(derived_member_type == underlying_member_type, resource.node,
                               'invalid.derived.resource',
                               'Arguments of derived resource are not matching underlying resource.')

        if not isinstance(self.program, VyperInterface):
            # Set analysed flag to True for all resources
            for resources in self.program.resources.values():
                for resource in resources:
                    resource.analysed = True

        for function in self.program.functions.values():
            with self._function_scope(function):
                for pre in function.preconditions:
                    self.annotate_expected(pre, types.VYPER_BOOL, resolve=True)

                for performs in function.performs:
                    self.annotate(performs, resolve=True)

                self.visit(function.node)
                self.resolve_type(function.node)

                for name, default in function.defaults.items():
                    if default:
                        self.annotate_expected(default, function.args[name].type, resolve=True)

                for post in function.postconditions:
                    self.annotate_expected(post, types.VYPER_BOOL, resolve=True)

                for check in function.checks:
                    self.annotate_expected(check, types.VYPER_BOOL, resolve=True)

                for loop_invariants in function.loop_invariants.values():
                    for loop_invariant in loop_invariants:
                        self.annotate_expected(loop_invariant, types.VYPER_BOOL, resolve=True)

        for lemma in self.program.lemmas.values():
            with self._function_scope(lemma):
                for stmt in lemma.node.body:
                    assert isinstance(stmt, ast.ExprStmt)
                    self.annotate_expected(stmt.value, types.VYPER_BOOL, resolve=True)

                for name, default in lemma.defaults.items():
                    if default:
                        self.annotate_expected(default, lemma.args[name].type, resolve=True)

                for pre in lemma.preconditions:
                    self.annotate_expected(pre, types.VYPER_BOOL, resolve=True)

        for ghost_function in self.program.ghost_function_implementations.values():
            assert isinstance(ghost_function, GhostFunction)
            with self._function_scope(ghost_function):
                expression_stmt = ghost_function.node.body[0]
                assert isinstance(expression_stmt, ast.ExprStmt)
                self.annotate_expected(expression_stmt.value, ghost_function.type.return_type, resolve=True)

        for inv in self.program.invariants:
            self.annotate_expected(inv, types.VYPER_BOOL, resolve=True)

        for post in self.program.general_postconditions:
            self.annotate_expected(post, types.VYPER_BOOL, resolve=True)

        for post in self.program.transitive_postconditions:
            self.annotate_expected(post, types.VYPER_BOOL, resolve=True)

        for check in self.program.general_checks:
            self.annotate_expected(check, types.VYPER_BOOL, resolve=True)

        if isinstance(self.program, VyperInterface):
            for caller_private in self.program.caller_private:
                self.annotate(caller_private, resolve=True)

    def resolve_type(self, node: ast.Node):
        if self.undecided_nodes:
            self.type_resolver.resolve_type(node)
            self.undecided_nodes = False

    def generic_visit(self, node: ast.Node, *args):
        assert False

    def pass_through(self, node1, node=None):
        vyper_types, nodes = self.visit(node1)
        if node is not None:
            nodes.append(node)
        return vyper_types, nodes

    def combine(self, node1, node2, node=None, allowed=lambda t: True):
        types1, nodes1 = self.visit(node1)
        types2, nodes2 = self.visit(node2)

        def is_array(t):
            return isinstance(t, ArrayType) and not t.is_strict

        def longest_array(matching, lst):
            try:
                arrays = [t for t in lst if is_array(t) and t.element_type == matching.element_type]
                return max(arrays, key=lambda t: t.size)
            except ValueError:
                raise InvalidProgramException(node if node is not None else node2, 'wrong.type')

        def intersect(l1, l2):
            for e in l1:
                if is_array(e):
                    yield longest_array(e, l2)
                else:
                    for t in l2:
                        if types.matches(e, t):
                            yield e
                        elif types.matches(t, e):
                            yield t

        intersection = list(filter(allowed, intersect(types1, types2)))
        if not intersection:
            raise InvalidProgramException(node if node is not None else node2, 'wrong.type')
        else:
            if node:
                return intersection, [*nodes1, *nodes2, node]
            else:
                return intersection, [*nodes1, *nodes2]

    def annotate(self, node1, node2=None, allowed=lambda t: True, resolve=False):
        if node2 is None:
            combined, nodes = self.visit(node1)
        else:
            combined, nodes = self.combine(node1, node2, allowed=allowed)
        for node in nodes:
            if len(combined) > 1:
                self.undecided_nodes = True
                node.type = combined
            else:
                node.type = combined[0]
        if resolve:
            self.resolve_type(node1)
            if node2 is not None:
                self.resolve_type(node2)

    def annotate_expected(self, node, expected, orelse=None, resolve=False):
        """
        Checks that node has type `expected` (or matches the predicate `expected`) or, if that isn't the case,
        that is has type `orelse` (or matches the predicate `orelse`).
        """
        tps, nodes = self.visit(node)

        def annotate_nodes(t):
            node.type = t
            for n in nodes:
                n.type = t
            if resolve:
                self.resolve_type(node)

        if isinstance(expected, VyperType):
            if any(types.matches(t, expected) for t in tps):
                annotate_nodes(expected)
                return
        else:
            for t in tps:
                if expected(t):
                    annotate_nodes(t)
                    return

        if orelse:
            self.annotate_expected(node, orelse)
        else:
            raise InvalidProgramException(node, 'wrong.type')

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for stmt in node.body:
            self.visit(stmt)

    def visit_Return(self, node: ast.Return):
        if node.value:
            # Interfaces are allowed to just have `pass` as a body instead of a correct return,
            # therefore we don't check for the correct return type.
            if self.program.is_interface():
                self.annotate(node.value)
            else:
                self.annotate_expected(node.value, self.current_func.type.return_type)

    def visit_Assign(self, node: ast.Assign):
        self.annotate(node.target, node.value)

    def visit_AugAssign(self, node: ast.AugAssign):
        self.annotate(node.target, node.value, types.is_numeric)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        # This is a variable declaration so we add it to the type map. Since Vyper
        # doesn't allow shadowing, we can just override the previous value.
        variable_name = node.target.id
        variable_type = self.type_builder.build(node.annotation)
        self.variables[variable_name] = [variable_type]
        self.annotate_expected(node.target, variable_type)

        if node.value:
            self.annotate_expected(node.value, variable_type)

    def visit_For(self, node: ast.For):
        self.annotate_expected(node.iter, lambda t: isinstance(t, ArrayType))

        # Add the loop variable to the type map
        var_name = node.target.id
        var_type = node.iter.type.element_type
        self.variables[var_name] = [var_type]

        self.annotate_expected(node.target, var_type)

        with self._loop_scope():
            self.current_loops[var_name] = node

            # Visit loop invariants
            for loop_inv in self.current_func.loop_invariants.get(node, []):
                self.annotate_expected(loop_inv, types.VYPER_BOOL)

            # Visit body
            for stmt in node.body:
                self.visit(stmt)

    def visit_If(self, node: ast.If):
        self.annotate_expected(node.test, types.VYPER_BOOL)
        for stmt in node.body + node.orelse:
            self.visit(stmt)

    def visit_Raise(self, node: ast.Raise):
        if node.msg:
            if not (isinstance(node.msg, ast.Name) and node.msg.id == names.UNREACHABLE):
                self.annotate(node.msg)

    def visit_Assert(self, node: ast.Assert):
        self.annotate_expected(node.test, types.VYPER_BOOL)

    def visit_ExprStmt(self, node: ast.ExprStmt):
        self.annotate(node.value)

    def visit_Log(self, node: ast.Log):
        _check(isinstance(node.body, ast.FunctionCall), node, 'invalid.log')
        assert isinstance(node.body, ast.FunctionCall)
        for arg in node.body.args:
            self.annotate(arg)
        for kw in node.body.keywords:
            self.annotate(kw.value)

    def visit_Pass(self, node: ast.Pass):
        pass

    def visit_Continue(self, node: ast.Continue):
        pass

    def visit_Break(self, node: ast.Break):
        pass

    def visit_BoolOp(self, node: ast.BoolOp):
        self.annotate_expected(node.left, types.VYPER_BOOL)
        self.annotate_expected(node.right, types.VYPER_BOOL)
        return [types.VYPER_BOOL], [node]

    def visit_Not(self, node: ast.Not):
        self.annotate_expected(node.operand, types.VYPER_BOOL)
        return [types.VYPER_BOOL], [node]

    def visit_ArithmeticOp(self, node: ast.ArithmeticOp):
        return self.combine(node.left, node.right, node, types.is_numeric)

    def visit_UnaryArithmeticOp(self, node: ast.UnaryArithmeticOp):
        return self.pass_through(node.operand, node)

    def visit_IfExpr(self, node: ast.IfExpr):
        self.annotate_expected(node.test, types.VYPER_BOOL)
        return self.combine(node.body, node.orelse, node)

    def visit_Comparison(self, node: ast.Comparison):
        self.annotate(node.left, node.right)
        return [types.VYPER_BOOL], [node]

    def visit_Containment(self, node: ast.Containment):
        self.annotate_expected(node.list, lambda t: isinstance(t, ArrayType))
        array_type = node.list.type
        assert isinstance(array_type, ArrayType)
        self.annotate_expected(node.value, array_type.element_type)
        return [types.VYPER_BOOL], [node]

    def visit_Equality(self, node: ast.Equality):
        self.annotate(node.left, node.right)
        return [types.VYPER_BOOL], [node]

    def visit_FunctionCall(self, node: ast.FunctionCall):
        name = node.name

        if node.resource:
            self._visit_resource(node.resource, node)

        with switch(name) as case:
            if case(names.CONVERT):
                self.check_number_of_arguments(node, 2)
                self.annotate(node.args[0])
                ntype = self.type_builder.build(node.args[1])
                return [ntype], [node]
            elif case(names.SUCCESS):
                self.check_number_of_arguments(node, 0, 1, allowed_keywords=[names.SUCCESS_IF_NOT])
                if node.args:
                    argument = node.args[0]
                    assert isinstance(argument, ast.ReceiverCall)
                    self.annotate(argument)
                    _check(isinstance(argument.receiver.type, types.SelfType), argument, 'spec.success',
                           'Only functions defined in this contract can be called from the specification.')
                return [types.VYPER_BOOL], [node]
            elif case(names.REVERT):
                self.check_number_of_arguments(node, 0, 1)
                if node.args:
                    argument = node.args[0]
                    assert isinstance(argument, ast.ReceiverCall)
                    self.annotate(argument)
                    _check(isinstance(argument.receiver.type, types.SelfType), argument, 'spec.success',
                           'Only functions defined in this contract can be called from the specification.')
                return [types.VYPER_BOOL], [node]
            elif case(names.FORALL):
                return self._visit_forall(node)
            elif case(names.ACCESSIBLE):
                return self._visit_accessible(node)
            elif case(names.EVENT):
                self.check_number_of_arguments(node, 1, 2)
                return self._visit_event(node)
            elif case(names.PREVIOUS):
                self.check_number_of_arguments(node, 1)
                self.annotate(node.args[0])
                loop = self._retrieve_loop(node, names.PREVIOUS)
                loop_array_type = loop.iter.type
                assert isinstance(loop_array_type, ArrayType)
                return [ArrayType(loop_array_type.element_type, loop_array_type.size, False)], [node]
            elif case(names.LOOP_ARRAY):
                self.check_number_of_arguments(node, 1)
                self.annotate(node.args[0])
                loop = self._retrieve_loop(node, names.LOOP_ARRAY)
                loop_array_type = loop.iter.type
                assert isinstance(loop_array_type, ArrayType)
                return [loop_array_type], [node]
            elif case(names.LOOP_ITERATION):
                self.check_number_of_arguments(node, 1)
                self.annotate(node.args[0])
                self._retrieve_loop(node, names.LOOP_ITERATION)
                return [types.VYPER_UINT256], [node]
            elif case(names.CALLER):
                self.check_number_of_arguments(node, 0)
                return [types.VYPER_ADDRESS], [node]
            elif case(names.RANGE):
                self.check_number_of_arguments(node, 1, 2)
                return self._visit_range(node)
            elif case(names.MIN) or case(names.MAX):
                self.check_number_of_arguments(node, 2)
                return self.combine(node.args[0], node.args[1], node, types.is_numeric)
            elif case(names.ADDMOD) or case(names.MULMOD):
                self.check_number_of_arguments(node, 3)
                for arg in node.args:
                    self.annotate_expected(arg, types.VYPER_UINT256)
                return [types.VYPER_UINT256], [node]
            elif case(names.SQRT):
                self.check_number_of_arguments(node, 1)
                self.annotate_expected(node.args[0], types.VYPER_DECIMAL)
                return [types.VYPER_DECIMAL], [node]
            elif case(names.SHIFT):
                self.check_number_of_arguments(node, 2)
                self.annotate_expected(node.args[0], types.VYPER_UINT256)
                self.annotate_expected(node.args[1], types.VYPER_INT128)
            elif case(names.BITWISE_NOT):
                self.check_number_of_arguments(node, 1)
                self.annotate_expected(node.args[0], types.VYPER_UINT256)
                return [types.VYPER_UINT256], [node]
            elif case(names.BITWISE_AND) or case(names.BITWISE_OR) or case(names.BITWISE_XOR):
                self.check_number_of_arguments(node, 2)
                self.annotate_expected(node.args[0], types.VYPER_UINT256)
                self.annotate_expected(node.args[1], types.VYPER_UINT256)
                return [types.VYPER_UINT256], [node]
            elif case(names.OLD) or case(names.PUBLIC_OLD) or case(names.ISSUED):
                self.check_number_of_arguments(node, 1)
                return self.pass_through(node.args[0], node)
            elif case(names.INDEPENDENT):
                self.check_number_of_arguments(node, 2)
                self.annotate(node.args[0])
                self.annotate(node.args[1])
                return [types.VYPER_BOOL], [node]
            elif case(names.REORDER_INDEPENDENT):
                self.check_number_of_arguments(node, 1)
                self.annotate(node.args[0])
                return [types.VYPER_BOOL], [node]
            elif case(names.FLOOR) or case(names.CEIL):
                self.check_number_of_arguments(node, 1)
                self.annotate_expected(node.args[0], types.VYPER_DECIMAL)
                return [types.VYPER_INT128], [node]
            elif case(names.LEN):
                self.check_number_of_arguments(node, 1)
                self.annotate_expected(node.args[0], lambda t: isinstance(t, types.ArrayType))
                return_type = select_version({'^0.2.0': types.VYPER_UINT256,
                                              '>=0.1.0-beta.16 <0.1.0': types.VYPER_INT128})
                return [return_type], [node]
            elif case(names.STORAGE):
                self.check_number_of_arguments(node, 1)
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                # We know that storage(self) has the self-type
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Name) and first_arg.id == names.SELF:
                    return [self.program.type, AnyStructType()], [node]
                # Otherwise it is just some struct, which we don't know anything about
                else:
                    return [AnyStructType()], [node]
            elif case(names.ASSERT_MODIFIABLE):
                self.check_number_of_arguments(node, 1)
                self.annotate_expected(node.args[0], types.VYPER_BOOL)
                return [None], [node]
            elif case(names.SEND):
                self.check_number_of_arguments(node, 2)
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                self.annotate_expected(node.args[1], types.VYPER_WEI_VALUE)
                return [None], [node]
            elif case(names.SELFDESTRUCT):
                self.check_number_of_arguments(node, 0, 1)
                if node.args:
                    # The selfdestruct Vyper function
                    self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                    return [None], [node]
                else:
                    # The selfdestruct verification function
                    return [types.VYPER_BOOL], [node]
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

                idx = first_index(lambda n: n.name == names.RAW_CALL_OUTSIZE, node.keywords)
                outsize_arg = node.keywords[idx].value
                assert isinstance(outsize_arg, ast.Num)
                size = outsize_arg.n
                return [ArrayType(types.VYPER_BYTE, size, False)], [node]
            elif case(names.RAW_LOG):
                self.check_number_of_arguments(node, 2)
                self.annotate_expected(node.args[0], ArrayType(types.VYPER_BYTES32, 4, False))
                self.annotate_expected(node.args[1], types.is_bytes_array)
                return [None], [node]
            elif case(names.CREATE_FORWARDER_TO):
                self.check_number_of_arguments(node, 1, allowed_keywords=[names.CREATE_FORWARDER_TO_VALUE])
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                if node.keywords:
                    self.annotate_expected(node.keywords[0].value, types.VYPER_WEI_VALUE)
                return [types.VYPER_ADDRESS], [node]
            elif case(names.AS_WEI_VALUE):
                self.check_number_of_arguments(node, 2)
                self.annotate_expected(node.args[0], types.is_integer)
                unit = node.args[1]
                _check(isinstance(unit, ast.Str) and
                       # Check that the unit exists
                       next((v for k, v in names.ETHER_UNITS.items() if unit.s in k), False),
                       node, 'invalid.unit')
                return [types.VYPER_WEI_VALUE], [node]
            elif case(names.AS_UNITLESS_NUMBER):
                self.check_number_of_arguments(node, 1)
                # We ignore units completely, therefore the type stays the same
                return self.pass_through(node.args[0], node)
            elif case(names.EXTRACT32):
                self.check_number_of_arguments(node, 2, allowed_keywords=[names.EXTRACT32_TYPE])
                self.annotate_expected(node.args[0], types.is_bytes_array)
                self.annotate_expected(node.args[1], types.VYPER_INT128)
                return_type = self.type_builder.build(node.keywords[0].value) if node.keywords else types.VYPER_BYTES32
                return [return_type], [node]
            elif case(names.CONCAT):
                _check(bool(node.args), node, 'invalid.no.args')

                for arg in node.args:
                    self.annotate_expected(arg, types.is_bytes_array)

                size = sum(arg.type.size for arg in node.args)
                return [ArrayType(node.args[0].type.element_type, size, False)], [node]
            elif case(names.KECCAK256) or case(names.SHA256):
                self.check_number_of_arguments(node, 1)
                self.annotate_expected(node.args[0], types.is_bytes_array)
                return [types.VYPER_BYTES32], [node]
            elif case(names.BLOCKHASH):
                self.check_number_of_arguments(node, 1)

                self.annotate_expected(node.args[0], types.VYPER_UINT256)
                return [types.VYPER_BYTES32], [node]
            elif case(names.METHOD_ID):
                if is_compatible_version('>=0.1.0-beta.16 <0.1.0'):
                    self.check_number_of_arguments(node, 2)

                    self.annotate_expected(node.args[0], lambda t: isinstance(t, StringType))
                    ntype = self.type_builder.build(node.args[1])
                elif is_compatible_version('^0.2.0'):
                    self.check_number_of_arguments(node, 1, allowed_keywords=[names.METHOD_ID_OUTPUT_TYPE])

                    self.annotate_expected(node.args[0], lambda t: isinstance(t, StringType))
                    ntype = types.ArrayType(types.VYPER_BYTE, 4)
                    for keyword in node.keywords:
                        if keyword.name == names.METHOD_ID_OUTPUT_TYPE:
                            ntype = self.type_builder.build(keyword.value)
                else:
                    assert False
                is_bytes32 = ntype == types.VYPER_BYTES32
                is_bytes4 = (isinstance(ntype, ArrayType) and ntype.element_type == types.VYPER_BYTE
                             and ntype.size == 4)
                _check(is_bytes32 or is_bytes4, node, 'invalid.method_id')
                return [ntype], [node]
            elif case(names.ECRECOVER):
                self.check_number_of_arguments(node, 4)
                self.annotate_expected(node.args[0], types.VYPER_BYTES32)
                self.annotate_expected(node.args[1], types.VYPER_UINT256)
                self.annotate_expected(node.args[2], types.VYPER_UINT256)
                self.annotate_expected(node.args[3], types.VYPER_UINT256)
                return [types.VYPER_ADDRESS], [node]
            elif case(names.ECADD) or case(names.ECMUL):
                self.check_number_of_arguments(node, 2)
                int_pair = ArrayType(types.VYPER_UINT256, 2)
                self.annotate_expected(node.args[0], int_pair)
                arg_type = int_pair if case(names.ECADD) else types.VYPER_UINT256
                self.annotate_expected(node.args[1], arg_type)
                return [int_pair], [node]
            elif case(names.EMPTY):
                self.check_number_of_arguments(node, 1)
                ntype = self.type_builder.build(node.args[0])
                return [ntype], [node]
            elif case(names.IMPLIES):
                self.check_number_of_arguments(node, 2)

                self.annotate_expected(node.args[0], types.VYPER_BOOL)
                self.annotate_expected(node.args[1], types.VYPER_BOOL)
                return [types.VYPER_BOOL], [node]
            elif case(names.RESULT):
                self.check_number_of_arguments(node, 0, 1, allowed_keywords=[names.RESULT_DEFAULT])
                if node.args:
                    argument = node.args[0]
                    _check(isinstance(argument, ast.ReceiverCall), argument, 'spec.result',
                           'Only functions defined in this contract can be called from the specification.')
                    assert isinstance(argument, ast.ReceiverCall)
                    self.annotate(argument)
                    _check(isinstance(argument.receiver.type, types.SelfType), argument, 'spec.result',
                           'Only functions defined in this contract can be called from the specification.')
                    func = self.program.functions[argument.name]

                    for kw in node.keywords:
                        self.annotate_expected(kw.value, func.type.return_type)
                    return [func.type.return_type], [node]
                elif len(node.keywords) > 0:
                    _check(False, node.keywords[0].value, 'spec.result',
                           'The default keyword argument can only be used in combination with a pure function.')
                return [self.current_func.type.return_type], [node]
            elif case(names.SUM):
                self.check_number_of_arguments(node, 1)

                def is_numeric_map_or_array(t):
                    return isinstance(t, types.MapType) and types.is_numeric(t.value_type) \
                           or isinstance(t, types.ArrayType) and types.is_numeric(t.element_type)

                self.annotate_expected(node.args[0], is_numeric_map_or_array)
                if isinstance(node.args[0].type, types.MapType):
                    vyper_type = node.args[0].type.value_type
                elif isinstance(node.args[0].type, types.ArrayType):
                    vyper_type = node.args[0].type.element_type
                else:
                    assert False
                return [vyper_type], [node]
            elif case(names.TUPLE):
                return self._visit_tuple(node.args), [node]
            elif case(names.SENT) or case(names.RECEIVED) or case(names.ALLOCATED):
                self.check_number_of_arguments(node, 0, 1, resources=1 if case(names.ALLOCATED) else 0)

                if not node.args:
                    map_type = types.MapType(types.VYPER_ADDRESS, types.NON_NEGATIVE_INT)
                    return [map_type], [node]
                else:
                    self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                    return [types.NON_NEGATIVE_INT], [node]
            elif case(names.LOCKED):
                self.check_number_of_arguments(node, 1)
                lock = node.args[0]
                _check(isinstance(lock, ast.Str) and lock.s in self.program.nonreentrant_keys(), node, 'invalid.lock')
                return [types.VYPER_BOOL], [node]
            elif case(names.OVERFLOW) or case(names.OUT_OF_GAS):
                self.check_number_of_arguments(node, 0)
                return [types.VYPER_BOOL], [node]
            elif case(names.FAILED):
                self.check_number_of_arguments(node, 1)
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                return [types.VYPER_BOOL], [node]
            elif case(names.IMPLEMENTS):
                self.check_number_of_arguments(node, 2)
                address = node.args[0]
                interface = node.args[1]
                is_interface = (isinstance(interface, ast.Name)
                                and (interface.id in self.program.interfaces
                                     or isinstance(self.program, VyperInterface) and interface.id == self.program.name))
                _check(is_interface, node, 'invalid.interface')
                self.annotate_expected(address, types.VYPER_ADDRESS)
                return [types.VYPER_BOOL], [node]
            elif case(names.INTERPRETED):
                self.check_number_of_arguments(node, 1)
                self.annotate_expected(node.args[0], types.VYPER_BOOL)
                return [types.VYPER_BOOL], [node]
            elif case(names.CONDITIONAL):
                self.check_number_of_arguments(node, 2)
                self.annotate_expected(node.args[0], types.VYPER_BOOL)
                return self.pass_through(node.args[1], node)
            elif case(names.REALLOCATE):
                keywords = [names.REALLOCATE_TO, names.REALLOCATE_ACTOR]
                required = [names.REALLOCATE_TO]
                self.check_number_of_arguments(node, 1, allowed_keywords=keywords,
                                               required_keywords=required, resources=1)
                self.annotate_expected(node.args[0], types.VYPER_WEI_VALUE)
                self.annotate_expected(node.keywords[0].value, types.VYPER_ADDRESS)
                for kw in node.keywords:
                    self.annotate_expected(kw.value, types.VYPER_ADDRESS)
                return [None], [node]
            elif case(names.FOREACH):
                return self._visit_foreach(node)
            elif case(names.OFFER):
                keywords = {
                    names.OFFER_TO: types.VYPER_ADDRESS,
                    names.OFFER_ACTOR: types.VYPER_ADDRESS,
                    names.OFFER_TIMES: types.VYPER_UINT256
                }
                required = [names.OFFER_TO, names.OFFER_TIMES]
                self.check_number_of_arguments(node, 2, allowed_keywords=keywords.keys(),
                                               required_keywords=required, resources=2)
                self.annotate_expected(node.args[0], types.VYPER_WEI_VALUE)
                self.annotate_expected(node.args[1], types.VYPER_WEI_VALUE)
                for kw in node.keywords:
                    self.annotate_expected(kw.value, keywords[kw.name])
                return [None], [node]
            elif case(names.ALLOW_TO_DECOMPOSE):
                self.check_number_of_arguments(node, 2, resources=1)
                self.annotate_expected(node.args[0], types.VYPER_WEI_VALUE)
                self.annotate_expected(node.args[1], types.VYPER_ADDRESS)
                return [None], [node]
            elif case(names.REVOKE):
                keywords = {
                    names.REVOKE_TO: types.VYPER_ADDRESS,
                    names.REVOKE_ACTOR: types.VYPER_ADDRESS
                }
                required = [names.REVOKE_TO]
                self.check_number_of_arguments(node, 2, allowed_keywords=keywords.keys(),
                                               required_keywords=required, resources=2)
                self.annotate_expected(node.args[0], types.VYPER_WEI_VALUE)
                self.annotate_expected(node.args[1], types.VYPER_WEI_VALUE)
                for kw in node.keywords:
                    self.annotate_expected(kw.value, keywords[kw.name])
                return [None], [node]
            elif case(names.EXCHANGE):
                keywords = [names.EXCHANGE_TIMES]
                self.check_number_of_arguments(node, 4, allowed_keywords=keywords,
                                               required_keywords=keywords, resources=2)
                self.annotate_expected(node.args[0], types.VYPER_WEI_VALUE)
                self.annotate_expected(node.args[1], types.VYPER_WEI_VALUE)
                self.annotate_expected(node.args[2], types.VYPER_ADDRESS)
                self.annotate_expected(node.args[3], types.VYPER_ADDRESS)
                self.annotate_expected(node.keywords[0].value, types.VYPER_UINT256)
                return [None], [node]
            elif case(names.CREATE):
                keywords = {
                    names.CREATE_TO: types.VYPER_ADDRESS,
                    names.CREATE_ACTOR: types.VYPER_ADDRESS
                }
                self.check_number_of_arguments(node, 1, allowed_keywords=keywords.keys(), resources=1)
                _check(node.resource is not None and node.underlying_resource is None, node, 'invalid.create',
                       'Only non-derived resources can be used with "create"')
                self.annotate_expected(node.args[0], types.VYPER_UINT256)
                for kw in node.keywords:
                    self.annotate_expected(kw.value, keywords[kw.name])
                return [None], [node]
            elif case(names.DESTROY):
                keywords = [names.DESTROY_ACTOR]
                self.check_number_of_arguments(node, 1, resources=1, allowed_keywords=keywords)
                _check(node.resource is not None and node.underlying_resource is None, node, 'invalid.destroy',
                       'Only non-derived resources can be used with "destroy"')
                self.annotate_expected(node.args[0], types.VYPER_UINT256)
                for kw in node.keywords:
                    self.annotate_expected(kw.value, types.VYPER_ADDRESS)
                return [None], [node]
            elif case(names.RESOURCE_PAYABLE):
                keywords = [names.RESOURCE_PAYABLE_ACTOR]
                self.check_number_of_arguments(node, 1, resources=1, allowed_keywords=keywords)
                _check(node.resource is None or node.underlying_resource is not None, node, 'invalid.payable',
                       'Only derived resources can be used with "payable"')
                self.annotate_expected(node.args[0], types.VYPER_UINT256)
                for kw in node.keywords:
                    self.annotate_expected(kw.value, types.VYPER_ADDRESS)
                return [None], [node]
            elif case(names.RESOURCE_PAYOUT):
                keywords = [names.RESOURCE_PAYOUT_ACTOR]
                self.check_number_of_arguments(node, 1, resources=1, allowed_keywords=keywords)
                _check(node.resource is None or node.underlying_resource is not None, node, 'invalid.payout',
                       'Only derived resources can be used with "payout"')
                self.annotate_expected(node.args[0], types.VYPER_UINT256)
                for kw in node.keywords:
                    self.annotate_expected(kw.value, types.VYPER_ADDRESS)
                return [None], [node]
            elif case(names.TRUST):
                keywords = [names.TRUST_ACTOR]
                self.check_number_of_arguments(node, 2, allowed_keywords=keywords)
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                self.annotate_expected(node.args[1], types.VYPER_BOOL)
                for kw in node.keywords:
                    self.annotate_expected(kw.value, types.VYPER_ADDRESS)
                return [None], [node]
            elif case(names.ALLOCATE_UNTRACKED):
                self.check_number_of_arguments(node, 1, resources=0)  # By setting resources to 0 we only allow wei.
                _check(node.resource is None or node.underlying_resource is not None, node,
                       'invalid.allocate_untracked', 'Only derived resources can be used with "allocate_untracked"')
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                return [None], [node]
            elif case(names.OFFERED):
                self.check_number_of_arguments(node, 4, resources=2)
                self.annotate_expected(node.args[0], types.VYPER_WEI_VALUE)
                self.annotate_expected(node.args[1], types.VYPER_WEI_VALUE)
                self.annotate_expected(node.args[2], types.VYPER_ADDRESS)
                self.annotate_expected(node.args[3], types.VYPER_ADDRESS)
                return [types.NON_NEGATIVE_INT], [node]
            elif case(names.NO_OFFERS):
                self.check_number_of_arguments(node, 1, resources=1)
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                return [types.VYPER_BOOL], [node]
            elif case(names.ALLOWED_TO_DECOMPOSE):
                self.check_number_of_arguments(node, 1, resources=1)
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                return [types.VYPER_UINT256], [node]
            elif case(names.TRUSTED):
                keywords = [names.TRUSTED_BY, names.TRUSTED_WHERE]
                required_keywords = [names.TRUSTED_BY]
                self.check_number_of_arguments(node, 1, allowed_keywords=keywords, required_keywords=required_keywords)
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                for kw in node.keywords:
                    self.annotate_expected(kw.value, types.VYPER_ADDRESS)
                return [types.VYPER_BOOL], [node]
            elif case(names.TRUST_NO_ONE):
                self.check_number_of_arguments(node, 2)
                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                self.annotate_expected(node.args[1], types.VYPER_ADDRESS)
                return [types.VYPER_BOOL], [node]
            elif len(node.args) == 1 and isinstance(node.args[0], ast.Dict):
                # This is a struct initializer
                self.check_number_of_arguments(node, 1)

                return self._visit_struct_init(node)
            elif name in self.program.contracts:
                # This is a contract initializer
                self.check_number_of_arguments(node, 1)

                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                return [self.program.contracts[name].type], [node]
            elif name in self.program.interfaces:
                # This is an interface initializer
                self.check_number_of_arguments(node, 1)

                self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
                return [self.program.interfaces[name].type], [node]
            elif name in self.program.ghost_functions:
                possible_functions = self.program.ghost_functions[name]
                if len(possible_functions) != 1:
                    if isinstance(self.program, VyperInterface):
                        function = [fun for fun in possible_functions if fun.file == self.program.file][0]
                    else:
                        implemented_interfaces = [self.program.interfaces[i.name].file for i in self.program.implements]
                        function = [fun for fun in possible_functions if fun.file in implemented_interfaces][0]
                else:
                    function = possible_functions[0]
                self.check_number_of_arguments(node, len(function.args) + 1)

                arg_types = [types.VYPER_ADDRESS, *[arg.type for arg in function.args.values()]]
                for arg_type, arg in zip(arg_types, node.args):
                    self.annotate_expected(arg, arg_type)

                return [function.type.return_type], [node]
            else:
                raise UnsupportedException(node, "Unsupported function call")

    def visit_ReceiverCall(self, node: ast.ReceiverCall):
        receiver = node.receiver

        if isinstance(receiver, ast.Name):
            # A lemma call
            if receiver.id == names.LEMMA:
                self.annotate(receiver)
                _check(not isinstance(receiver.type, (ContractType, InterfaceType)),
                       receiver,  'invalid.lemma.receiver',
                       'A receiver, with name "lemma" and with a contract- or interface-type, is not supported.')

                lemma = self.program.lemmas[node.name]
                self.check_number_of_arguments(node, len(lemma.args))
                for arg, func_arg in zip(node.args, lemma.args.values()):
                    self.annotate_expected(arg, func_arg.type)

                return [types.VYPER_BOOL], [node]
            # A receiver ghost function call
            elif receiver.id in self.program.interfaces.keys():
                self.annotate(receiver)
                function = self.program.interfaces[receiver.id].own_ghost_functions[node.name]
                self.check_number_of_arguments(node, len(function.args) + 1)

                arg_types = [types.VYPER_ADDRESS, *[arg.type for arg in function.args.values()]]
                for arg_type, arg in zip(arg_types, node.args):
                    self.annotate_expected(arg, arg_type)

                return [function.type.return_type], [node]

        def expected(t):
            is_self_call = isinstance(t, SelfType)
            is_external_call = isinstance(t, (ContractType, InterfaceType))
            is_log = t is None
            return is_self_call or is_external_call or is_log

        self.annotate_expected(receiver, expected)
        receiver_type = receiver.type

        # A self call
        if isinstance(receiver_type, SelfType):
            function = self.program.functions[node.name]
            num_args = len(function.args)
            num_defaults = len(function.defaults)
            self.check_number_of_arguments(node, *range(num_args - num_defaults, num_args + 1))
            for arg, func_arg in zip(node.args, function.args.values()):
                self.annotate_expected(arg, func_arg.type)
            return [function.type.return_type], [node]
        else:

            for arg in node.args:
                self.annotate(arg)

            for kw in node.keywords:
                self.annotate(kw.value)

            # A logging call
            if not receiver_type:
                return [None], [node]
            # A contract call
            elif isinstance(receiver_type, ContractType):
                return [receiver_type.function_types[node.name].return_type], [node]
            elif isinstance(receiver_type, InterfaceType):
                interface = self.program.interfaces[receiver_type.name]
                function = interface.functions[node.name]
                return [function.type.return_type], [node]
            else:
                assert False

    def _visit_resource_address(self, node: ast.Node, resource_name: str, interface: Optional[VyperInterface] = None):
        self.annotate_expected(node, types.VYPER_ADDRESS)
        _check(resource_name != names.UNDERLYING_WEI, node, 'invalid.resource.address',
               'The underlying wei resource cannot have an address.')
        is_wei = resource_name == names.WEI

        ref_interface = None
        if isinstance(node, ast.Name):
            ref_interface = self.program
        elif isinstance(node, ast.Attribute):
            for field, field_type in self.program.fields.type.member_types.items():
                if node.attr == field:
                    _check(isinstance(field_type, types.InterfaceType), node, 'invalid.resource.address')
                    assert isinstance(field_type, types.InterfaceType)
                    ref_interface = self.program.interfaces[field_type.name]
                    _check(is_wei or resource_name in ref_interface.own_resources, node, 'invalid.resource.address')
                    break
            else:
                _check(False, node, 'invalid.resource.address')
        elif isinstance(node, ast.FunctionCall):
            if node.name in self.program.ghost_functions:
                if isinstance(self.program, VyperInterface):
                    function = self.program.ghost_functions[node.name][0]
                else:
                    function = self.program.ghost_function_implementations.get(node.name)
                    if function is None:
                        function = self.program.ghost_functions[node.name][0]
                _check(isinstance(function.type.return_type, types.InterfaceType), node, 'invalid.resource.address')
                assert isinstance(function.type.return_type, types.InterfaceType)
                program = first(interface for interface in self.program.interfaces.values()
                                if interface.file == function.file) or self.program
                ref_interface = program.interfaces[function.type.return_type.name]
            else:
                self.check_number_of_arguments(node, 1)
                ref_interface = self.program.interfaces[node.name]

            _check(is_wei or resource_name in ref_interface.own_resources, node, 'invalid.resource.address')
        elif isinstance(node, ast.ReceiverCall):
            assert node.name in self.program.ghost_functions
            assert isinstance(node.receiver, ast.Name)
            interface_name = node.receiver.id
            function = self.program.interfaces[interface_name].own_ghost_functions.get(node.name)
            _check(isinstance(function.type.return_type, types.InterfaceType), node, 'invalid.resource.address')
            assert isinstance(function.type.return_type, types.InterfaceType)
            program = first(interface for interface in self.program.interfaces.values()
                            if interface.file == function.file) or self.program
            ref_interface = program.interfaces[function.type.return_type.name]

            _check(is_wei or resource_name in ref_interface.own_resources, node, 'invalid.resource.address')
        else:
            assert False

        if not is_wei and ref_interface is not None:
            if interface is not None:
                if isinstance(ref_interface, VyperInterface):
                    _check(ref_interface.file == interface.file, node, 'invalid.resource.address')
                else:
                    interface_names = [t.name for t in ref_interface.implements]
                    interfaces = [ref_interface.interfaces[name] for name in interface_names]
                    files = [ref_interface.file] + [i.file for i in interfaces]
                    _check(interface.file in files, node, 'invalid.resource.address')
            elif isinstance(ref_interface, VyperInterface):
                self_is_interface = isinstance(self.program, VyperInterface)
                self_does_not_have_resource = resource_name not in self.program.own_resources
                _check(self_is_interface or self_does_not_have_resource, node, 'invalid.resource.address')

    def _annotate_resource(self, node: ast.Node, top: bool = False):
        if isinstance(node, ast.Name):
            resources = self.program.resources.get(node.id)
            if resources is not None and len(resources) == 1:
                resource = resources[0]
                if self.program.config.has_option(names.CONFIG_NO_DERIVED_WEI):
                    _check(resource.name != names.WEI, node, 'invalid.resource')
                if (top and self.program.file != resource.file
                        and resource.name != names.WEI
                        and resource.name != names.UNDERLYING_WEI):
                    interface = first(i for i in self.program.interfaces.values() if i.file == resource.file)
                    _check(any(i.name == interface.name for i in self.program.implements), node, 'invalid.resource')
                    _check(node.id in interface.declared_resources, node, 'invalid.resource')
            else:
                resource = self.program.declared_resources.get(node.id)
            args = []
        elif isinstance(node, ast.FunctionCall) and node.name == names.CREATOR:
            resource, args = self._annotate_resource(node.args[0])
            node.type = node.args[0].type
        elif isinstance(node, ast.FunctionCall):
            resources = self.program.resources.get(node.name)
            if resources is not None and len(resources) == 1:
                resource = resources[0]
            else:
                resource = self.program.declared_resources.get(node.name)
            if self.program.config.has_option(names.CONFIG_NO_DERIVED_WEI):
                _check(resource.name != names.WEI, node, 'invalid.resource')
            if node.resource is not None:
                assert isinstance(node.resource, ast.Expr)
                self._visit_resource_address(node.resource, node.name)
                resource.own_address = node.resource
            elif (top and self.program.file != resource.file
                    and resource.name != names.WEI
                    and resource.name != names.UNDERLYING_WEI):
                interface = first(i for i in self.program.interfaces.values() if i.file == resource.file)
                _check(any(i.name == interface.name for i in self.program.implements), node, 'invalid.resource')
                _check(node.name in interface.declared_resources, node, 'invalid.resource')
            args = node.args
        elif isinstance(node, ast.Attribute):
            assert isinstance(node.value, ast.Name)
            interface = self.program.interfaces[node.value.id]
            if top:
                _check(any(i.name == interface.name for i in self.program.implements), node, 'invalid.resource')
                _check(node.attr in interface.declared_resources, node, 'invalid.resource')
            resource = interface.declared_resources.get(node.attr)
            args = []
        elif isinstance(node, ast.ReceiverCall):
            address = None
            if isinstance(node.receiver, ast.Name):
                interface = self.program.interfaces[node.receiver.id]
                if top:
                    _check(any(i.name == interface.name for i in self.program.implements), node, 'invalid.resource')
                    _check(node.name in interface.declared_resources, node, 'invalid.resource')
            elif isinstance(node.receiver, ast.Subscript):
                assert isinstance(node.receiver.value, ast.Attribute)
                assert isinstance(node.receiver.value.value, ast.Name)
                interface_name = node.receiver.value.value.id
                interface = self.program.interfaces[interface_name]
                if top:
                    _check(node.name in interface.declared_resources, node, 'invalid.resource')
                address = node.receiver.index
                self._visit_resource_address(address, node.name, interface)
            else:
                assert False
            resource = interface.declared_resources.get(node.name)
            resource.own_address = address
            args = node.args
        elif isinstance(node, ast.Subscript):
            address = node.index
            resource, args = self._annotate_resource(node.value)
            node.type = node.value.type
            interface = None
            if isinstance(node.value, ast.Name):
                resource_name = node.value.id
            elif isinstance(node.value, ast.Attribute):
                assert isinstance(node.value.value, ast.Name)
                interface = self.program.interfaces[node.value.value.id]
                resource_name = node.value.attr
                _check(resource_name in interface.declared_resources, node, 'invalid.resource')
            else:
                assert False
            self._visit_resource_address(address, resource_name, interface)
            resource.own_address = address
        else:
            assert False

        if not resource:
            raise InvalidProgramException(node, 'invalid.resource',
                                          f'Could not find a resource for node:\n{pprint(node, True)}')

        for arg_type, arg in zip(resource.type.member_types.values(), args):
            self.annotate_expected(arg, arg_type)

        node.type = resource.type
        return resource, args

    def _visit_resource(self, node: ast.Node, top_node: Optional[ast.FunctionCall] = None):
        if isinstance(node, ast.Exchange):
            self._visit_resource(node.left, top_node)
            self._visit_resource(node.right, top_node)
            return

        resource, args = self._annotate_resource(node, True)

        if len(args) != len(resource.type.member_types):
            raise InvalidProgramException(node, 'invalid.resource')

        if top_node is not None and top_node.underlying_resource is None:
            top_node.underlying_resource = resource.underlying_resource

    def _add_quantified_vars(self, var_decls: ast.Dict):
        vars_types = zip(var_decls.keys, var_decls.values)
        for name, type_annotation in vars_types:
            var_type = self.type_builder.build(type_annotation)
            self.variables[name.id] = [var_type]
            name.type = var_type

    def _visit_forall(self, node: ast.FunctionCall):
        with self._quantified_vars_scope():
            # Add the quantified variables {<x1>: <t1>, <x2>: <t2>, ...} to the
            # variable map
            first_arg = node.args[0]
            assert isinstance(first_arg, ast.Dict)
            self._add_quantified_vars(first_arg)

            # Triggers can have any type
            for arg in node.args[1:-1]:
                self.annotate(arg)

            # The quantified expression is always a Boolean
            self.annotate_expected(node.args[-1], types.VYPER_BOOL)

        return [types.VYPER_BOOL], [node]

    def _visit_foreach(self, node: ast.FunctionCall):
        with self._quantified_vars_scope():
            # Add the quantified variables {<x1>: <t1>, <x2>: <t2>, ...} to the
            # variable map
            first_arg = node.args[0]
            assert isinstance(first_arg, ast.Dict)
            self._add_quantified_vars(first_arg)

            # Triggers can have any type
            for arg in node.args[1:-1]:
                self.annotate(arg)

            # Annotate the body
            self.annotate(node.args[-1])

        return [None], [node]

    def _visit_accessible(self, node: ast.FunctionCall):
        self.annotate_expected(node.args[0], types.VYPER_ADDRESS)
        self.annotate_expected(node.args[1], types.VYPER_WEI_VALUE)

        if len(node.args) == 3:
            function_call = node.args[2]
            assert isinstance(function_call, ast.ReceiverCall)
            function = self.program.functions[function_call.name]
            for arg, arg_type in zip(function_call.args, function.type.arg_types):
                self.annotate_expected(arg, arg_type)

        return [types.VYPER_BOOL], [node]

    def _visit_event(self, node: ast.FunctionCall):
        event = node.args[0]
        assert isinstance(event, ast.FunctionCall)
        event_name = event.name
        event_type = self.program.events[event_name].type

        for arg, arg_type in zip(event.args, event_type.arg_types):
            self.annotate_expected(arg, arg_type)

        if len(node.args) == 2:
            self.annotate_expected(node.args[1], types.VYPER_UINT256)

        return [types.VYPER_BOOL], [node]

    def _visit_struct_init(self, node: ast.FunctionCall):
        ntype = self.program.structs[node.name].type

        struct_dict = node.args[0]
        assert isinstance(struct_dict, ast.Dict)

        for key, value in zip(struct_dict.keys, struct_dict.values):
            value_type = ntype.member_types[key.id]
            self.annotate_expected(value, value_type)

        return [ntype], [node]

    def _visit_range(self, node: ast.FunctionCall):
        _check(len(node.args) > 0, node, 'invalid.range')
        first_arg = node.args[0]
        self.annotate_expected(first_arg, types.is_integer)

        if len(node.args) == 1:
            # A range expression of the form 'range(n)' where 'n' is a constant
            assert isinstance(first_arg, ast.Num)
            size = first_arg.n
        elif len(node.args) == 2:
            second_arg = node.args[1]
            self.annotate_expected(second_arg, types.is_integer)
            if isinstance(second_arg, ast.ArithmeticOp) \
                    and second_arg.op == ast.ArithmeticOperator.ADD \
                    and ast.compare_nodes(first_arg, second_arg.left):
                assert isinstance(second_arg.right, ast.Num)
                # A range expression of the form 'range(x, x + n)' where 'n' is a constant
                size = second_arg.right.n
            else:
                assert isinstance(first_arg, ast.Num) and isinstance(second_arg, ast.Num)
                # A range expression of the form 'range(n1, n2)' where 'n1' and 'n2 are constants
                size = second_arg.n - first_arg.n
        else:
            raise InvalidProgramException(node, 'invalid.range')

        _check(size > 0, node, 'invalid.range', 'The size of a range(...) must be greater than zero.')
        return [ArrayType(types.VYPER_INT128, size, True)], [node]

    def _retrieve_loop(self, node, name):
        loop_var_name = node.args[0].id
        loop = self.current_loops.get(loop_var_name)
        _check(loop is not None, node, f"invalid.{name}")
        return loop

    @staticmethod
    def visit_Bytes(node: ast.Bytes):
        # Bytes could either be non-strict or (if it has length 32) strict
        non_strict = types.ArrayType(types.VYPER_BYTE, len(node.s), False)
        if len(node.s) == 32:
            return [non_strict, types.VYPER_BYTES32], [node]
        else:
            return [non_strict], [node]

    @staticmethod
    def visit_Str(node: ast.Str):
        string_bytes = bytes(node.s, 'utf-8')
        ntype = StringType(len(string_bytes))
        return [ntype], [node]

    # Sets occur in trigger expressions
    def visit_Set(self, node: ast.Set):
        for elem in node.elements:
            # Triggers can have any type
            self.annotate(elem)
        return [None], [node]

    @staticmethod
    def visit_Num(node: ast.Num):
        if isinstance(node.n, int):
            max_int128 = 2 ** 127 - 1
            max_address = 2 ** 160 - 1
            if 0 <= node.n <= max_int128:
                tps = [types.VYPER_INT128,
                       types.VYPER_UINT256,
                       types.VYPER_ADDRESS,
                       types.VYPER_BYTES32]
            elif max_int128 < node.n <= max_address:
                tps = [types.VYPER_UINT256,
                       types.VYPER_ADDRESS,
                       types.VYPER_BYTES32]
            elif max_address < node.n:
                tps = [types.VYPER_UINT256,
                       types.VYPER_BYTES32]
            else:
                tps = [types.VYPER_INT128]
            nodes = [node]
            return tps, nodes
        elif isinstance(node.n, Decimal):
            return [types.VYPER_DECIMAL], [node]
        else:
            assert False

    @staticmethod
    def visit_Bool(node: ast.Bool):
        return [types.VYPER_BOOL], [node]

    def visit_Attribute(self, node: ast.Attribute):
        self.annotate_expected(node.value, lambda t: isinstance(t, StructType), types.VYPER_ADDRESS)
        struct_type = node.value.type if isinstance(node.value.type, StructType) else types.AddressType()
        ntype = struct_type.member_types.get(node.attr)
        if not ntype:
            raise InvalidProgramException(node, 'invalid.storage.var')
        return [ntype], [node]

    def visit_Subscript(self, node: ast.Subscript):
        self.annotate_expected(node.value, lambda t: isinstance(t, (ArrayType, MapType)))
        if isinstance(node.value.type, MapType):
            key_type = node.value.type.key_type
            self.annotate_expected(node.index, key_type)
            ntype = node.value.type.value_type
        elif isinstance(node.value.type, ArrayType):
            self.annotate_expected(node.index, types.is_integer)
            ntype = node.value.type.element_type
        else:
            assert False

        return [ntype], [node]

    def visit_Name(self, node: ast.Name):
        _check(node.id in self.variables, node, 'invalid.local.var')
        return self.variables[node.id], [node]

    def visit_List(self, node: ast.List):
        # Vyper guarantees that size > 0
        size = len(node.elements)
        for e in node.elements:
            self.annotate(e)
        element_types = [e.type for e in node.elements]
        possible_types = []
        for element_type in element_types:
            if isinstance(element_type, list):
                if possible_types:
                    possible_types = [t for t in possible_types if t in element_type]
                else:
                    possible_types = element_type
            else:
                _check(not possible_types or element_type in possible_types, node, 'invalid.element.types')
                possible_types = [element_type]
                break

        return [types.ArrayType(element_type, size) for element_type in possible_types], [node]

    def visit_Tuple(self, node: ast.Tuple):
        return self._visit_tuple(node.elements), [node]

    def _visit_tuple(self, elements):
        length = len(elements)
        for e in elements:
            self.annotate(e)
        element_types = [e.type if isinstance(e.type, list) else [e.type] for e in elements]
        sizes = [len(element_type) for element_type in element_types]
        index = [0] * length
        possible_types = []
        while True:
            possible_type = TupleType([element_types[i][index[i]] for i in range(length)])
            possible_types.append(possible_type)
            for i in range(length):
                index[i] = (index[i] + 1) % sizes[i]
                if index[i]:
                    break
            else:
                break
        return possible_types


class TypeResolver(NodeVisitor):

    def resolve_type(self, node: ast.Node):
        self.visit(node, None)

    def visit(self, node, *args):
        assert len(args) == 1
        if hasattr(node, "type"):
            if isinstance(node.type, list):
                node.type = args[0] or node.type[0]
        return super().visit(node, *args)

    @staticmethod
    def first_intersect(left, right):
        if not isinstance(left, list):
            left = [left]
        if not isinstance(right, list):
            right = [right]
        for t in left:
            if t in right:
                return t

    def visit_Assign(self, node: ast.Assign, _: Optional[VyperType]):
        self.visit(node.target, self.first_intersect(node.target.type, node.value.type))
        return self.visit(node.value, node.target.type)

    def visit_AugAssign(self, node: ast.AugAssign, _: Optional[VyperType]):
        self.visit(node.target, self.first_intersect(node.target.type, node.value.type))
        return self.visit(node.value, node.target.type)

    def visit_Comparison(self, node: ast.Comparison, _: Optional[VyperType]):
        self.visit(node.left, self.first_intersect(node.left.type, node.right.type))
        return self.visit(node.right, node.left.type)

    def visit_Equality(self, node: ast.Equality, _: Optional[VyperType]):
        self.visit(node.left, self.first_intersect(node.left.type, node.right.type))
        return self.visit(node.right, node.left.type)

    def visit_FunctionCall(self, node: ast.FunctionCall, _: Optional[VyperType]):
        self.generic_visit(node, None)

    def visit_ReceiverCall(self, node: ast.ReceiverCall, _: Optional[VyperType]):
        return self.generic_visit(node, None)

    def visit_Set(self, node: ast.Set, _: Optional[VyperType]):
        return self.generic_visit(node, None)

    def visit_List(self, node: ast.List, _: Optional[VyperType]):
        return self.generic_visit(node, node.type.element_type)
