"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os

from contextlib import contextmanager

from typing import Optional, Dict, Union, List

from twovyper.parsing.lark import copy_pos_from
from twovyper.utils import switch, first

from twovyper.parsing import lark
from twovyper.parsing.preprocessor import preprocess
from twovyper.parsing.transformer import transform

from twovyper.ast import ast_nodes as ast, interfaces, names
from twovyper.ast.visitors import NodeVisitor, NodeTransformer

from twovyper.ast.nodes import (
    VyperProgram, VyperFunction, VyperStruct, VyperContract, VyperEvent, VyperVar,
    Config, VyperInterface, GhostFunction, Resource
)
from twovyper.ast.types import (
    TypeBuilder, FunctionType, EventType, SelfType, InterfaceType, ResourceType,
    StructType, ContractType, DerivedResourceType
)

from twovyper.exceptions import InvalidProgramException, UnsupportedException


def parse(path: str, root: Optional[str], as_interface=False, name=None, parse_level=0) -> VyperProgram:
    with open(path, 'r') as file:
        contract = file.read()

    preprocessed_contract = preprocess(contract)
    contract_ast = lark.parse_module(preprocessed_contract, contract, path)
    contract_ast = transform(contract_ast)
    program_builder = ProgramBuilder(path, root, as_interface, name, parse_level)
    return program_builder.build(contract_ast)


class ProgramBuilder(NodeVisitor):
    """
    The program builder creates a Vyper program out of the AST. It collects contract
    state variables and functions. It should only be used by calling the build method once.
    """

    # Pre and postconditions are only allowed before a function. As we walk through all
    # top-level statements we gather pre and postconditions until we reach a function
    # definition.

    def __init__(self, path: str, root: Optional[str], is_interface: bool, name: str, parse_level: int):
        self.path = os.path.abspath(path)
        self.root = root
        self.is_interface = is_interface
        self.name = name
        self.parse_further_interfaces = parse_level <= 3
        self.parse_level = parse_level

        self.config = None

        self.field_types = {}
        self.functions = {}
        self.lemmas = {}
        self.function_counter = 0
        self.interfaces = {}
        self.structs = {}
        self.contracts = {}
        self.events = {}
        self.resources = {}
        self.local_state_invariants = []
        self.inter_contract_invariants = []
        self.general_postconditions = []
        self.transitive_postconditions = []
        self.general_checks = []
        self.implements = []
        self.additional_implements = []
        self.ghost_functions = {}
        self.ghost_function_implementations = {}

        self.postconditions = []
        self.preconditions = []
        self.checks = []
        self.caller_private = []
        self.performs = []

        self.is_preserves = False

    @property
    def type_builder(self):
        type_map = {}
        for name, struct in self.structs.items():
            type_map[name] = struct.type
        for name, contract in self.contracts.items():
            type_map[name] = contract.type
        for name, interface in self.interfaces.items():
            type_map[name] = interface.type

        return TypeBuilder(type_map, not self.parse_further_interfaces)

    def build(self, node) -> VyperProgram:
        self.visit(node)
        # No trailing local specs allowed
        self._check_no_local_spec()

        self.config = self.config or Config([])

        if self.config.has_option(names.CONFIG_ALLOCATION):
            # Add wei underlying resource
            underlying_wei_type = ResourceType(names.UNDERLYING_WEI, {})
            underlying_wei_resource = Resource(underlying_wei_type, None, None)
            self.resources[names.UNDERLYING_WEI] = underlying_wei_resource
            # Create a fake node for the underlying wei resource
            fake_node = ast.Name(names.UNDERLYING_WEI)
            copy_pos_from(node, fake_node)
            fake_node.is_ghost_code = True
            if not self.config.has_option(names.CONFIG_NO_DERIVED_WEI):
                # Add wei derived resource
                wei_type = DerivedResourceType(names.WEI, {}, underlying_wei_type)
                wei_resource = Resource(wei_type, None, None, fake_node)
                self.resources[names.WEI] = wei_resource

        if self.is_interface:
            interface_type = InterfaceType(self.name)
            if self.parse_level <= 2:
                return VyperInterface(node,
                                      self.path,
                                      self.name,
                                      self.config,
                                      self.functions,
                                      self.interfaces,
                                      self.resources,
                                      self.local_state_invariants,
                                      self.inter_contract_invariants,
                                      self.general_postconditions,
                                      self.transitive_postconditions,
                                      self.general_checks,
                                      self.caller_private,
                                      self.ghost_functions,
                                      interface_type)
            else:
                return VyperInterface(node,
                                      self.path,
                                      self.name,
                                      self.config, {}, {},
                                      self.resources,
                                      [], [], [], [], [], [],
                                      self.ghost_functions,
                                      interface_type,
                                      is_stub=True)
        else:
            if self.caller_private:
                node = first(self.caller_private)
                raise InvalidProgramException(node, 'invalid.caller.private',
                                              'Caller private is only allowed in interfaces')
            # Create the self-type
            self_type = SelfType(self.field_types)
            self_struct = VyperStruct(names.SELF, self_type, None)

            return VyperProgram(node,
                                self.path,
                                self.config,
                                self_struct,
                                self.functions,
                                self.interfaces,
                                self.structs,
                                self.contracts,
                                self.events,
                                self.resources,
                                self.local_state_invariants,
                                self.inter_contract_invariants,
                                self.general_postconditions,
                                self.transitive_postconditions,
                                self.general_checks,
                                self.lemmas,
                                self.implements,
                                self.implements + self.additional_implements,
                                self.ghost_function_implementations)

    def _check_no_local_spec(self):
        """
        Checks that there are no specifications for functions pending, i.e. there
        are no local specifications followed by either global specifications or eof.
        """

        if self.postconditions:
            cond = "Postcondition"
            node = self.postconditions[0]
        elif self.checks:
            cond = "Check"
            node = self.checks[0]
        elif self.performs:
            cond = "Performs"
            node = self.performs[0]
        else:
            return
        raise InvalidProgramException(node, 'local.spec', f"{cond} only allowed before function")

    def _check_no_ghost_function(self):
        if self.ghost_functions:
            cond = "Ghost function declaration"
            node = first(self.ghost_functions.values()).node
        elif self.ghost_function_implementations:
            cond = "Ghost function definition"
            node = first(self.ghost_function_implementations.values()).node
        else:
            return
        raise InvalidProgramException(node, 'invalid.ghost', f'{cond} only allowed after "#@ interface"')

    def _check_no_lemmas(self):
        if self.lemmas:
            raise InvalidProgramException(first(self.lemmas.values()).node, 'invalid.lemma',
                                          'Lemmas are not allowed in interfaces')

    def generic_visit(self, node: ast.Node, *args):
        raise InvalidProgramException(node, 'invalid.spec')

    def visit_Module(self, node: ast.Module):
        for stmt in node.stmts:
            self.visit(stmt)

    def visit_ExprStmt(self, node: ast.ExprStmt):
        if not isinstance(node.value, ast.Str):
            # Long string comment, ignore.
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        if node.is_ghost_code:
            raise InvalidProgramException(node, 'invalid.ghost.code')

        if not self.parse_further_interfaces:
            return

        files = {}
        for alias in node.names:
            components = alias.name.split('.')
            components[-1] = f'{components[-1]}.vy'
            path = os.path.join(self.root or '', *components)
            files[path] = alias.asname.value if hasattr(alias.asname, 'value') else alias.asname

        for file, name in files.items():
            if name in [names.SELF, names.LOG, names.LEMMA, *names.ENV_VARIABLES]:
                raise UnsupportedException(node, 'Invalid file name.')
            interface = parse(file, self.root, True, name, self.parse_level + 1)
            self.interfaces[name] = interface

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.is_ghost_code:
            raise InvalidProgramException(node, 'invalid.ghost.code')

        module = node.module or ''
        components = module.split('.')

        if not self.parse_further_interfaces:
            return

        if components == interfaces.VYPER_INTERFACES:
            for alias in node.names:
                name = alias.name
                if name == interfaces.ERC20:
                    self.contracts[name] = VyperContract(name, interfaces.ERC20_TYPE, None)
                elif name == interfaces.ERC721:
                    self.contracts[name] = VyperContract(name, interfaces.ERC721_TYPE, None)
                else:
                    assert False

            return

        if node.level == 0:
            path = os.path.join(self.root or '', *components)
        else:
            path = self.path
            for _ in range(node.level):
                path = os.path.dirname(path)

            path = os.path.join(path, *components)

        files = {}
        for alias in node.names:
            name = alias.name
            interface_path = os.path.join(path, f'{name}.vy')
            files[interface_path] = name

        for file, name in files.items():
            if name in [names.SELF, names.LOG, names.LEMMA, *names.ENV_VARIABLES]:
                raise UnsupportedException(node, 'Invalid file name.')
            interface = parse(file, self.root, True, name, self.parse_level + 1)
            self.interfaces[name] = interface

    def visit_StructDef(self, node: ast.StructDef):
        vyper_type = self.type_builder.build(node)
        assert isinstance(vyper_type, StructType)
        struct = VyperStruct(node.name, vyper_type, node)
        self.structs[struct.name] = struct

    def visit_EventDef(self, node: ast.EventDef):
        vyper_type = self.type_builder.build(node)
        if isinstance(vyper_type, EventType):
            event = VyperEvent(node.name, vyper_type)
            self.events[node.name] = event

    def visit_FunctionStub(self, node: ast.FunctionStub):
        # A function stub on the top-level is a resource declaration
        self._check_no_local_spec()

        name, is_derived = Resource.get_name_and_derived_flag(node)

        if name in self.resources or name in names.SPECIAL_RESOURCES:
            raise InvalidProgramException(node, 'duplicate.resource')

        vyper_type = self.type_builder.build(node)
        if isinstance(vyper_type, ResourceType):
            if is_derived:
                resource = Resource(vyper_type, node, self.path, node.returns)
            else:
                resource = Resource(vyper_type, node, self.path)
            self.resources[name] = resource

    def visit_ContractDef(self, node: ast.ContractDef):
        if node.is_ghost_code:
            raise InvalidProgramException(node, 'invalid.ghost.code')

        vyper_type = self.type_builder.build(node)
        if isinstance(vyper_type, ContractType):
            contract = VyperContract(node.name, vyper_type, node)
            self.contracts[contract.name] = contract

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if node.is_ghost_code:
            raise InvalidProgramException(node, 'invalid.ghost.code')

        # No local specs are allowed before contract state variables
        self._check_no_local_spec()

        variable_name = node.target.id
        if variable_name == names.IMPLEMENTS:
            interface_name = node.annotation.id
            if interface_name not in [interfaces.ERC20, interfaces.ERC721] or interface_name in self.interfaces:
                interface_type = InterfaceType(interface_name)
                self.implements.append(interface_type)
            elif interface_name in [interfaces.ERC20, interfaces.ERC721]:
                interface_type = InterfaceType(interface_name)
                self.additional_implements.append(interface_type)
        # We ignore the units declarations
        elif variable_name != names.UNITS:
            variable_type = self.type_builder.build(node.annotation)
            if isinstance(variable_type, EventType):
                event = VyperEvent(variable_name, variable_type)
                self.events[variable_name] = event
            else:
                self.field_types[variable_name] = variable_type

    def visit_Assign(self, node: ast.Assign):
        # This is for invariants and postconditions which get translated to
        # assignments during preprocessing.

        name = node.target.id

        if name != names.GENERAL_POSTCONDITION and self.is_preserves:
            msg = f"Only general postconditions are allowed in preserves. ({name} is not allowed)"
            raise InvalidProgramException(node, 'invalid.preserves', msg)

        with switch(name) as case:
            if case(names.CONFIG):
                if isinstance(node.value, ast.Name):
                    options = [node.value.id]
                elif isinstance(node.value, ast.Tuple):
                    options = [n.id for n in node.value.elements]

                for option in options:
                    if option not in names.CONFIG_OPTIONS:
                        msg = f"Option {option} is invalid."
                        raise InvalidProgramException(node, 'invalid.config.option', msg)

                if self.config is not None:
                    raise InvalidProgramException(node, 'invalid.config', 'The "config" is specified multiple times.')
                self.config = Config(options)
            elif case(names.INTERFACE):
                self._check_no_local_spec()
                self._check_no_ghost_function()
                self._check_no_lemmas()
                self.is_interface = True
            elif case(names.INVARIANT):
                # No local specifications allowed before invariants
                self._check_no_local_spec()

                self.local_state_invariants.append(node.value)
            elif case(names.INTER_CONTRACT_INVARIANTS):
                # No local specifications allowed before inter contract invariants
                self._check_no_local_spec()

                self.inter_contract_invariants.append(node.value)
            elif case(names.GENERAL_POSTCONDITION):
                # No local specifications allowed before general postconditions
                self._check_no_local_spec()

                if self.is_preserves:
                    self.transitive_postconditions.append(node.value)
                else:
                    self.general_postconditions.append(node.value)
            elif case(names.GENERAL_CHECK):
                # No local specifications allowed before general check
                self._check_no_local_spec()

                self.general_checks.append(node.value)
            elif case(names.POSTCONDITION):
                self.postconditions.append(node.value)
            elif case(names.PRECONDITION):
                self.preconditions.append(node.value)
            elif case(names.CHECK):
                self.checks.append(node.value)
            elif case(names.CALLER_PRIVATE):
                # No local specifications allowed before caller private
                self._check_no_local_spec()

                self.caller_private.append(node.value)
            elif case(names.PERFORMS):
                self.performs.append(node.value)
            else:
                assert False

    def visit_If(self, node: ast.If):
        # This is a preserves clause, since we replace all preserves clauses with if statements
        # when preprocessing
        if self.is_preserves:
            raise InvalidProgramException(node, 'preserves.in.preserves')

        self.is_preserves = True
        for stmt in node.body:
            self.visit(stmt)
        self.is_preserves = False

    def _arg(self, node: ast.Arg) -> VyperVar:
        arg_name = node.name
        arg_type = self.type_builder.build(node.annotation)
        return VyperVar(arg_name, arg_type, node)

    def visit_Ghost(self, node: ast.Ghost):
        for func in node.body:

            def check_ghost(cond):
                if not cond:
                    raise InvalidProgramException(func, 'invalid.ghost')

            check_ghost(isinstance(func, ast.FunctionDef))
            assert isinstance(func, ast.FunctionDef)
            check_ghost(len(func.body) == 1)
            func_body = func.body[0]
            check_ghost(isinstance(func_body, ast.ExprStmt))
            assert isinstance(func_body, ast.ExprStmt)
            check_ghost(func.returns)

            decorators = [dec.name for dec in func.decorators]
            check_ghost(len(decorators) == len(func.decorators))

            name = func.name
            args = {arg.name: self._arg(arg) for arg in func.args}
            arg_types = [arg.type for arg in args.values()]
            return_type = None if func.returns is None else self.type_builder.build(func.returns)
            vyper_type = FunctionType(arg_types, return_type)

            if names.IMPLEMENTS in decorators:
                check_ghost(not self.is_interface)
                check_ghost(len(decorators) == 1)

                ghost_functions = self.ghost_function_implementations
            else:
                check_ghost(self.is_interface)
                check_ghost(not decorators)
                check_ghost(isinstance(func_body.value, ast.Ellipsis))

                ghost_functions = self.ghost_functions

            if name in ghost_functions:
                raise InvalidProgramException(func, 'duplicate.ghost')

            ghost_functions[name] = GhostFunction(name, args, vyper_type, func, self.path)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        args = {arg.name: self._arg(arg) for arg in node.args}
        defaults = {arg.name: arg.default for arg in node.args}
        arg_types = [arg.type for arg in args.values()]
        return_type = None if node.returns is None else self.type_builder.build(node.returns)
        vyper_type = FunctionType(arg_types, return_type)
        decs = node.decorators
        loop_invariant_transformer = LoopInvariantTransformer()
        loop_invariant_transformer.visit(node)
        function = VyperFunction(node.name, self.function_counter, args, defaults, vyper_type,
                                 self.postconditions, self.preconditions, self.checks,
                                 loop_invariant_transformer.loop_invariants, self.performs, decs, node)
        if node.is_lemma:
            if node.decorators:
                decorator = node.decorators[0]
                if len(node.decorators) > 1 or decorator.name != names.INTERPRETED_DECORATOR:
                    raise InvalidProgramException(decorator, 'invalid.lemma',
                                                  f'A lemma can have only one decorator: {names.INTERPRETED_DECORATOR}')
                if not decorator.is_ghost_code:
                    raise InvalidProgramException(decorator, 'invalid.lemma',
                                                  'The decorator of a lemma must be ghost code')
            if vyper_type.return_type is not None:
                raise InvalidProgramException(node, 'invalid.lemma', 'A lemma cannot have a return type')
            if node.name in self.lemmas:
                raise InvalidProgramException(node, 'duplicate.lemma')
            if self.is_interface:
                raise InvalidProgramException(node, 'invalid.lemma', 'Lemmas are not allowed in interfaces')
            self.lemmas[node.name] = function
        else:
            for decorator in node.decorators:
                if decorator.is_ghost_code and decorator.name != names.PURE:
                    raise InvalidProgramException(decorator, 'invalid.ghost.code')
            self.functions[node.name] = function
        self.function_counter += 1
        # Reset local specs
        self.postconditions = []
        self.preconditions = []
        self.checks = []
        self.performs = []


class LoopInvariantTransformer(NodeTransformer):
    """
    Replaces all constants in the AST by their value.
    """

    def __init__(self):
        self._last_loop: Union[ast.For, None] = None
        self._possible_loop_invariant_nodes: List[ast.Assign] = []
        self.loop_invariants: Dict[ast.For, List[ast.Expr]] = {}

    @contextmanager
    def _in_loop_scope(self, node: ast.For):
        possible_loop_invariant_nodes = self._possible_loop_invariant_nodes
        last_loop = self._last_loop
        self._last_loop = node

        yield

        self._possible_loop_invariant_nodes = possible_loop_invariant_nodes
        self._last_loop = last_loop

    def visit_Assign(self, node: ast.Assign):
        if node.is_ghost_code:
            if isinstance(node.target, ast.Name) and node.target.id == names.INVARIANT:
                if self._last_loop and node in self._possible_loop_invariant_nodes:
                    self.loop_invariants.setdefault(self._last_loop, []).append(node.value)
                else:
                    raise InvalidProgramException(node, 'invalid.loop.invariant',
                                                  'You may only write loop invariants at beginning in loops')
                return None

        return node

    def visit_For(self, node: ast.For):
        with self._in_loop_scope(node):
            self._possible_loop_invariant_nodes = []
            for n in node.body:
                if isinstance(n, ast.Assign) and n.is_ghost_code and n.target.id == names.INVARIANT:
                    self._possible_loop_invariant_nodes.append(n)
                else:
                    break
            return self.generic_visit(node)
