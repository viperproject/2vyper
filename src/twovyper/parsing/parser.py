"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os

from typing import Optional

from twovyper.parsing import lark
from twovyper.parsing.preprocessor import preprocess
from twovyper.parsing.transformer import transform

from twovyper.ast import ast_nodes as ast, interfaces, names
from twovyper.ast.visitors import NodeVisitor

from twovyper.ast.nodes import (
    VyperProgram, VyperFunction, VyperStruct, VyperContract, VyperEvent, VyperVar,
    Config, VyperInterface, GhostFunction, Resource
)
from twovyper.ast.types import TypeBuilder, FunctionType, EventType, SelfType, InterfaceType, ResourceType

from twovyper.exceptions import InvalidProgramException


def parse(path: str, root: Optional[str], as_interface=False, name=None) -> VyperProgram:
    with open(path, 'r') as file:
        contract = file.read()

    preprocessed_contract = preprocess(contract)
    contract_ast = lark.parse_module(preprocessed_contract, contract, path)
    contract_ast = transform(contract_ast)
    program_builder = ProgramBuilder(path, root, as_interface, name)
    return program_builder.build(contract_ast)


class ProgramBuilder(NodeVisitor):
    """
    The program builder creates a Vyper program out of the AST. It collects contract
    state variables and functions. It should only be used by calling the build method once.
    """

    # Pre and postconditions are only allowed before a function. As we walk through all
    # top-level statements we gather pre and postconditions until we reach a function
    # definition.

    def __init__(self, path: str, root: Optional[str], is_interface: bool, name: str):
        self.path = path
        self.root = root
        self.is_interface = is_interface
        self.name = name

        self.config = None

        self.field_types = {}
        self.functions = {}
        self.interfaces = {}
        self.structs = {}
        self.contracts = {}
        self.events = {}
        self.resources = {}
        self.invariants = []
        self.general_postconditions = []
        self.transitive_postconditions = []
        self.general_checks = []
        self.implements = []
        self.ghost_functions = {}
        self.ghost_function_implementations = {}

        self.postconditions = []
        self.checks = []
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

        return TypeBuilder(type_map)

    def build(self, node) -> VyperProgram:
        self.visit(node)
        # No trailing local specs allowed
        self._check_no_local_spec()

        self.config = self.config or Config([])

        if self.is_interface:
            interface_type = InterfaceType(self.name)
            return VyperInterface(node,
                                  self.path,
                                  self.name,
                                  self.config,
                                  self.functions,
                                  self.ghost_functions,
                                  self.general_postconditions,
                                  interface_type)
        else:
            # Create the self-type
            self_type = SelfType(self.field_types)
            self_struct = VyperStruct(names.SELF, self_type, None)

            # Add wei resource
            if self.config.has_option(names.CONFIG_ALLOCATION):
                wei_type = ResourceType(names.WEI, {})
                wei_resource = Resource(names.WEI, wei_type, None)
                self.resources[names.WEI] = wei_resource

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
                                self.invariants,
                                self.general_postconditions,
                                self.transitive_postconditions,
                                self.general_checks,
                                self.implements,
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

    def generic_visit(self, node: ast.Node, *args):
        raise InvalidProgramException(node, 'invalid.spec')

    def visit_Module(self, node: ast.Module):
        for stmt in node.stmts:
            self.visit(stmt)

    def visit_Import(self, node: ast.Import):
        files = {}
        for alias in node.names:
            components = alias.name.split('.')
            components[-1] = f'{components[-1]}.vy'
            path = os.path.join(self.root or '', *components)
            files[path] = alias.asname

        for file, name in files.items():
            interface = parse(file, self.root, True, name)
            self.interfaces[name] = interface

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ''
        components = module.split('.')

        if self.is_interface:
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
            interface = parse(file, self.root, True, name)
            self.interfaces[name] = interface

    def visit_StructDef(self, node: ast.StructDef):
        type = self.type_builder.build(node)
        struct = VyperStruct(node.name, type, node)
        self.structs[struct.name] = struct

    def visit_FunctionStub(self, node: ast.FunctionStub):
        # A function stub on the top-level is a resource declaration
        self._check_no_local_spec()

        if node.name in self.resources or node.name == names.CREATOR:
            raise InvalidProgramException(node, 'duplicate.resource')

        type = self.type_builder.build(node)
        resource = Resource(node.name, type, node)
        self.resources[node.name] = resource

    def visit_ContractDef(self, node: ast.ContractDef):
        type = self.type_builder.build(node)
        contract = VyperContract(node.name, type, node)
        self.contracts[contract.name] = contract

    def visit_AnnAssign(self, node: ast.AnnAssign):
        # No local specs are allowed before contract state variables
        self._check_no_local_spec()

        variable_name = node.target.id
        if variable_name == names.IMPLEMENTS:
            if node.annotation.id not in [interfaces.ERC20, interfaces.ERC721]:
                interface_type = InterfaceType(node.annotation.id)
                self.implements.append(interface_type)
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

        if name == names.CONFIG:
            if isinstance(node.value, ast.Name):
                options = [node.value.id]
            elif isinstance(node.value, ast.Tuple):
                options = [n.id for n in node.value.elements]

            for option in options:
                if option not in names.CONFIG_OPTIONS:
                    msg = f"Option {option} is invalid."
                    raise InvalidProgramException(node, 'invalid.config.option', msg)

            self.config = Config(options)
        elif name == names.INTERFACE:
            self._check_no_local_spec()
            self.is_interface = True
        elif name == names.INVARIANT:
            # No local specifications allowed before invariants
            self._check_no_local_spec()

            self.invariants.append(node.value)
        elif name == names.GENERAL_POSTCONDITION:
            # No local specifications allowed before general postconditions
            self._check_no_local_spec()

            if self.is_preserves:
                self.transitive_postconditions.append(node.value)
            else:
                self.general_postconditions.append(node.value)
        elif name == names.GENERAL_CHECK:
            # No local specifications allowed before general check
            self._check_no_local_spec()

            self.general_checks.append(node.value)
        elif name == names.POSTCONDITION:
            self.postconditions.append(node.value)
        elif name == names.CHECK:
            self.checks.append(node.value)
        elif name == names.PERFORMS:
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
            check_ghost(len(func.body) == 1)
            check_ghost(isinstance(func.body[0], ast.ExprStmt))
            check_ghost(func.returns)

            decorators = [dec.name for dec in func.decorators]
            check_ghost(len(decorators) == len(func.decorators))

            name = func.name
            args = {arg.name: self._arg(arg) for arg in func.args}
            arg_types = [arg.type for arg in args.values()]
            return_type = None if func.returns is None else self.type_builder.build(func.returns)
            type = FunctionType(arg_types, return_type)

            if names.IMPLEMENTS in decorators:
                check_ghost(len(decorators) == 1)

                ghost_functions = self.ghost_function_implementations
            else:
                check_ghost(not decorators)
                check_ghost(isinstance(func.body[0].value, ast.Ellipsis))

                ghost_functions = self.ghost_functions

            if name in ghost_functions:
                raise InvalidProgramException(func, 'duplicate.ghost')

            ghost_functions[name] = GhostFunction(name, args, type, func)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        args = {arg.name: self._arg(arg) for arg in node.args}
        defaults = {arg.name: arg.default for arg in node.args}
        arg_types = [arg.type for arg in args.values()]
        return_type = None if node.returns is None else self.type_builder.build(node.returns)
        type = FunctionType(arg_types, return_type)
        decs = node.decorators
        function = VyperFunction(node.name, args, defaults, type,
                                 self.postconditions, self.checks, self.performs, decs, node)
        if function.is_private() and self.checks:
            msg = f"Private functions are not allowed to have checks."
            raise InvalidProgramException(node, 'invalid.checks', msg)
        self.functions[node.name] = function
        # Reset local specs
        self.postconditions = []
        self.checks = []
        self.performs = []
