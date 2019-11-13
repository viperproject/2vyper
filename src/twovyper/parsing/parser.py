"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast
import os

from typing import List, Optional

from twovyper.parsing import lark
from twovyper.parsing.preprocessor import preprocess
from twovyper.parsing.transformer import transform

from twovyper.ast import names
from twovyper.ast import types

from twovyper.ast.nodes import (
    VyperProgram, VyperFunction, VyperStruct, VyperContract, VyperEvent, VyperVar,
    VyperConfig, VyperInterface, GhostFunction
)

from twovyper.ast.types import (
    TypeBuilder, FunctionType, EventType, StructType, SelfType, ContractType, InterfaceType
)

from twovyper.exceptions import InvalidProgramException


def parse(path: str, root: Optional[str], as_interface=False, name=None) -> VyperProgram:
    with open(path, 'r') as file:
        contract = file.read()

    preprocessed_contract = preprocess(contract)
    contract_ast = lark.parse(preprocessed_contract)
    contract_ast = transform(contract_ast)
    program_builder = ProgramBuilder(path, root, as_interface, name)
    return program_builder.build(contract_ast)


class ProgramBuilder(ast.NodeVisitor):
    """
    The program builder creates a Vyper program out of the AST. It collects contract
    state variables and functions. It should only be used by calling the build method once.
    """

    # Pre and postconditions are only allowed before a function. As we walk through all
    # top-level statements we gather pre and postconditions until we reach a function
    # definition.

    def __init__(self, path: str, root: str, is_interface: bool, name: str):
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
        self.invariants = []
        self.general_postconditions = []
        self.transitive_postconditions = []
        self.general_checks = []
        self.implements = []
        self.ghost_functions = {}

        self.postconditions = []
        self.checks = []

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

        self.config = self.config or VyperConfig([])

        if self.is_interface:
            interface_type = InterfaceType(self.name)
            return VyperInterface(self.path,
                                  self.name,
                                  self.config,
                                  self.functions,
                                  self.ghost_functions,
                                  self.general_postconditions,
                                  interface_type)
        else:
            # Add self.balance
            assert not self.field_types.get(names.SELF_BALANCE)
            self.field_types[names.SELF_BALANCE] = types.VYPER_WEI_VALUE

            # Create the self-type
            self_type = SelfType(self.field_types)
            self_struct = VyperStruct(names.SELF, self_type, None)
            return VyperProgram(self.path,
                                self.config,
                                self_struct,
                                self.functions,
                                self.interfaces,
                                self.structs,
                                self.contracts,
                                self.events,
                                self.invariants,
                                self.general_postconditions,
                                self.transitive_postconditions,
                                self.general_checks,
                                self.implements)

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
        else:
            return
        raise InvalidProgramException(node, 'local.spec', f"{cond} only allowed before function")

    def generic_visit(self, node: ast.AST):
        raise InvalidProgramException(node, 'invalid.spec')

    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
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
        # TODO: check for ERC20

        module = node.module or ''
        components = module.split('.')

        if self.is_interface or (components and components[0] == 'vyper'):
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

    def visit_ClassDef(self, node: ast.ClassDef):
        type = self.type_builder.build(node)
        if isinstance(type, StructType):
            struct = VyperStruct(node.name, type, node)
            self.structs[struct.name] = struct
        elif isinstance(type, ContractType):
            contract = VyperContract(node.name, type, node)
            self.contracts[contract.name] = contract
        else:
            assert False

    def visit_AnnAssign(self, node):
        # No local specs are allowed before contract state variables
        self._check_no_local_spec()

        variable_name = node.target.id
        if variable_name == names.IMPLEMENTS:
            # TODO: handle ERC20
            if node.annotation.id not in ['ERC20', 'ERC721']:
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

    def visit_Assign(self, node):
        # This is for invariants and postconditions which get translated to
        # assignments during preprocessing.

        assert len(node.targets) == 1
        name = node.targets[0].id

        if name == names.CONFIG:
            if isinstance(node.value, ast.Name):
                options = [node.value.id]
            elif isinstance(node.value, ast.Tuple):
                options = [n.id for n in node.value.elts]

            for option in options:
                if option not in names.CONFIG_OPTIONS:
                    msg = f"Option {option} is invalid."
                    raise InvalidProgramException(node, 'invalid.config.option', msg)

            self.config = VyperConfig(options)
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

    def visit_With(self, node: ast.With):
        # This is a ghost clause, since we replace all ghost clauses with with statements
        # when preprocessing
        for func in node.body:

            def check_ghost(cond):
                if not cond:
                    raise InvalidProgramException(func, 'invalid.ghost')

            check_ghost(isinstance(func, ast.FunctionDef))
            check_ghost(len(func.body) == 1)
            check_ghost(isinstance(func.body[0], ast.Expr))
            check_ghost(isinstance(func.body[0].value, ast.Ellipsis))
            check_ghost(func.returns)

            name = func.name
            args, _ = LocalProgramBuilder(self.type_builder).build(func)
            arg_types = [arg.type for arg in args.values()]
            return_type = None if func.returns is None else self.type_builder.build(func.returns)
            type = FunctionType(arg_types, return_type)
            if name in self.ghost_functions:
                raise InvalidProgramException(func, 'duplicate.ghost')
            self.ghost_functions[name] = GhostFunction(name, args, type, func)

    def _decorators(self, node: ast.FunctionDef) -> List[str]:
        return [dec.id for dec in node.decorator_list if isinstance(dec, ast.Name)]

    def visit_FunctionDef(self, node):
        local = LocalProgramBuilder(self.type_builder)
        args, local_vars = local.build(node)
        arg_types = [arg.type for arg in args.values()]
        return_type = None if node.returns is None else self.type_builder.build(node.returns)
        type = FunctionType(arg_types, return_type)
        decs = self._decorators(node)
        function = VyperFunction(node.name, args, local_vars, type,
                                 self.postconditions, self.checks, decs, node)
        self.functions[node.name] = function
        # Reset local specs
        self.postconditions = []
        self.checks = []


class LocalProgramBuilder(ast.NodeVisitor):

    def __init__(self, type_builder: TypeBuilder):
        self.args = {}
        self.local_vars = {}

        self.type_builder = type_builder

    def build(self, node: ast.AST):
        self.visit(node)
        return self.args, self.local_vars

    def visit_arg(self, node: ast.arg):
        arg_name = node.arg
        arg_type = self.type_builder.build(node.annotation)
        var = VyperVar(arg_name, arg_type, node)
        self.args[arg_name] = var

    def visit_AnnAssign(self, node: ast.AnnAssign):
        variable_name = node.target.id
        variable_type = self.type_builder.build(node.annotation)
        var = VyperVar(variable_name, variable_type, node)
        self.local_vars[variable_name] = var

    def visit_For(self, node: ast.For):
        # We ignore these variables as they are added in the type annotator
        self.generic_visit(node)
