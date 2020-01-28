"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Dict, Iterable, List, Optional, Set, Tuple

from twovyper.ast import ast_nodes as ast, names
from twovyper.ast.types import (
    VyperType, FunctionType, StructType, ResourceType, ContractType, EventType, InterfaceType
)


class Config:

    def __init__(self, options: List[str]):
        self.options = options

    def has_option(self, option: str) -> bool:
        return option in self.options


class VyperVar:

    def __init__(self, name: str, type: VyperType, node):
        self.name = name
        self.type = type
        self.node = node


class VyperFunction:

    def __init__(self,
                 name: str,
                 args: Dict[str, VyperVar],
                 defaults: Dict[str, Optional[ast.Expr]],
                 type: FunctionType,
                 postconditions: List[ast.Expr],
                 checks: List[ast.Expr],
                 decorators: List[ast.Decorator],
                 node: Optional[ast.FunctionDef]):
        self.name = name
        self.args = args
        self.defaults = defaults
        self.type = type
        self.postconditions = postconditions
        self.checks = checks
        self.decorators = decorators
        self.node = node
        # Gets set in the analyzer
        self.analysis = None

    @property
    def _decorator_names(self) -> Iterable[str]:
        for dec in self.decorators:
            yield dec.name

    def is_public(self) -> bool:
        return names.PUBLIC in self._decorator_names

    def is_private(self) -> bool:
        return names.PRIVATE in self._decorator_names

    def is_payable(self) -> bool:
        return names.PAYABLE in self._decorator_names

    def is_constant(self) -> bool:
        return names.CONSTANT in self._decorator_names

    def nonreentrant_keys(self) -> Iterable[str]:
        for dec in self.decorators:
            if dec.name == names.NONREENTRANT:
                yield dec.args[0].s


class GhostFunction:

    def __init__(self,
                 name: str,
                 args: Dict[str, VyperVar],
                 type: FunctionType,
                 node: ast.FunctionDef):
        self.name = name
        self.args = args
        self.type = type
        self.node = node


class VyperStruct:

    def __init__(self,
                 name: str,
                 type: StructType,
                 node: Optional[ast.Node]):
        self.name = name
        self.type = type
        self.node = node


class Resource(VyperStruct):

    def __init__(self,
                 name: str,
                 type: ResourceType,
                 node: Optional[ast.Node]):
        super().__init__(name, type, node)


class VyperContract:

    def __init__(self, name: str, type: ContractType, node: Optional[ast.ContractDef]):
        self.name = name
        self.type = type
        self.node = node


class VyperEvent:

    def __init__(self, name: str, type: EventType):
        self.name = name
        self.type = type


class VyperProgram:

    def __init__(self,
                 node: ast.Module,
                 file: str,
                 config: Config,
                 fields: VyperStruct,
                 functions: Dict[str, VyperFunction],
                 interfaces: Dict[str, 'VyperInterface'],
                 structs: Dict[str, VyperStruct],
                 contracts: Dict[str, VyperContract],
                 events: Dict[str, VyperEvent],
                 resources: Dict[str, VyperStruct],
                 invariants: List[ast.Expr],
                 general_postconditions: List[ast.Expr],
                 transitive_postconditions: List[ast.Expr],
                 general_checks: List[ast.Expr],
                 implements: List[InterfaceType],
                 ghost_function_implementations: Dict[str, ast.Expr]):
        self.node = node
        self.file = file
        self.config = config
        self.fields = fields
        self.functions = functions
        self.interfaces = interfaces
        self.structs = structs
        self.contracts = contracts
        self.events = events
        self.resources = resources
        self.invariants = invariants
        self.general_postconditions = general_postconditions
        self.transitive_postconditions = transitive_postconditions
        self.general_checks = general_checks
        self.implements = implements
        self.ghost_functions = dict(self._ghost_functions())
        self.ghost_function_implementations = ghost_function_implementations
        self.type = fields.type
        # Is set in the analyzer
        self.analysis = None

    def is_interface(self) -> bool:
        return False

    def nonreentrant_keys(self) -> Set[str]:
        s = set()
        for func in self.functions.values():
            for key in func.nonreentrant_keys():
                s.add(key)
        return s

    def _ghost_functions(self) -> Iterable[Tuple[str, GhostFunction]]:
        for interface in self.interfaces.values():
            for name, func in interface.ghost_functions.items():
                yield name, func


class VyperInterface(VyperProgram):

    def __init__(self,
                 node: ast.Module,
                 file: str,
                 name: Optional[str],
                 config: Config,
                 functions: Dict[str, VyperFunction],
                 ghost_functions: Dict[str, GhostFunction],
                 general_postconditions: List[ast.Expr],
                 type: InterfaceType):
        struct_name = f'{name}$self'
        empty_struct_type = StructType(struct_name, {})
        empty_struct = VyperStruct(struct_name, empty_struct_type, None)
        super().__init__(node,
                         file,
                         config,
                         empty_struct,
                         functions,
                         {}, {}, {}, {}, {},
                         [],
                         general_postconditions,
                         [], [], [], {})
        self.name = name
        self.ghost_functions = ghost_functions
        self.type = type

    def is_interface(self) -> bool:
        return True
