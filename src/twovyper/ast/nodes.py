"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import os
from collections import defaultdict
from itertools import chain
from typing import Dict, Iterable, List, Optional, Set, Tuple, TYPE_CHECKING

from twovyper.ast import ast_nodes as ast, names
from twovyper.ast.types import (
    VyperType, FunctionType, StructType, ResourceType, ContractType, EventType, InterfaceType, DerivedResourceType
)
if TYPE_CHECKING:
    from twovyper.analysis.analyzer import FunctionAnalysis, ProgramAnalysis


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
                 index: int,
                 args: Dict[str, VyperVar],
                 defaults: Dict[str, Optional[ast.Expr]],
                 type: FunctionType,
                 postconditions: List[ast.Expr],
                 preconditions: List[ast.Expr],
                 checks: List[ast.Expr],
                 loop_invariants: Dict[ast.For, List[ast.Expr]],
                 performs: List[ast.FunctionCall],
                 decorators: List[ast.Decorator],
                 node: Optional[ast.FunctionDef]):
        self.name = name
        self.index = index
        self.args = args
        self.defaults = defaults
        self.type = type
        self.postconditions = postconditions
        self.preconditions = preconditions
        self.checks = checks
        self.loop_invariants = loop_invariants
        self.performs = performs
        self.decorators = decorators
        self.node = node
        # Gets set in the analyzer
        self.analysis: Optional[FunctionAnalysis] = None

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

    def is_pure(self) -> bool:
        return names.PURE in self._decorator_names

    def is_interpreted(self) -> bool:
        return names.INTERPRETED_DECORATOR in self._decorator_names

    def nonreentrant_keys(self) -> Iterable[str]:
        for dec in self.decorators:
            if dec.name == names.NONREENTRANT:
                yield dec.args[0].s


class GhostFunction:

    def __init__(self,
                 name: str,
                 args: Dict[str, VyperVar],
                 type: FunctionType,
                 node: ast.FunctionDef,
                 file: str):
        self.name = name
        self.args = args
        self.type = type
        self.node = node
        self.file = file

    @property
    def interface(self):
        return os.path.split(self.file)[1].split('.')[0] if self.file else ''


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
                 rtype: ResourceType,
                 node: Optional[ast.Node],
                 file: Optional[str],
                 underlying_resource_node: Optional[ast.Expr] = None):
        super().__init__(rtype.name, rtype, node)
        self.file = file
        self.analysed = False
        self._own_address = None
        self.underlying_resource = underlying_resource_node
        self.underlying_address = None
        self.derived_resources = []

    @property
    def interface(self):
        return os.path.split(self.file)[1].split('.')[0] if self.file else ''

    @property
    def underlying_resource_name(self):
        return self.type.underlying_resource.name if isinstance(self.type, DerivedResourceType) else None

    @property
    def own_address(self):
        if self.analysed:
            raise AssertionError("The own address attribute is only available during the analysing phase.")
        return self._own_address

    @own_address.setter
    def own_address(self, expr: ast.Expr):
        self._own_address = expr

    def is_derived_resource(self):
        return self.underlying_resource_name is not None

    @staticmethod
    def get_name_and_derived_flag(node) -> Tuple[str, bool]:
        if node.name.startswith(names.DERIVED_RESOURCE_PREFIX):
            return node.name[len(names.DERIVED_RESOURCE_PREFIX):], True
        assert node.name.startswith(names.RESOURCE_PREFIX)
        return node.name[len(names.RESOURCE_PREFIX):], False


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
                 resources: Dict[str, Resource],
                 local_state_invariants: List[ast.Expr],
                 inter_contract_invariants: List[ast.Expr],
                 general_postconditions: List[ast.Expr],
                 transitive_postconditions: List[ast.Expr],
                 general_checks: List[ast.Expr],
                 lemmas: Dict[str, VyperFunction],
                 implements: List[InterfaceType],
                 real_implements: List[InterfaceType],
                 ghost_function_implementations: Dict[str, GhostFunction]):
        self.node = node
        self.file = file
        self.config = config
        self.fields = fields
        self.functions = functions
        self.interfaces = interfaces
        self.structs = structs
        self.contracts = contracts
        self.events = events
        self.imported_resources: Dict[str, List[Resource]] = defaultdict(list)
        for key, value in self._resources():
            self.imported_resources[key].append(value)
        self.own_resources = resources
        self.declared_resources = dict((name, resource) for name, resource in self.own_resources.items()
                                       if name != names.WEI and name != names.UNDERLYING_WEI)
        self.resources: Dict[str, List[Resource]] = defaultdict(list, self.imported_resources)
        for key, value in resources.items():
            self.resources[key].append(value)
        self.local_state_invariants = local_state_invariants
        self.inter_contract_invariants = inter_contract_invariants
        self.general_postconditions = general_postconditions
        self.transitive_postconditions = transitive_postconditions
        self.general_checks = general_checks
        self.lemmas = lemmas
        self.implements = implements
        self.real_implements = real_implements
        self.ghost_functions: Dict[str, List[GhostFunction]] = defaultdict(list)
        for key, value in self._ghost_functions():
            self.ghost_functions[key].append(value)
        self.ghost_function_implementations = ghost_function_implementations
        self.type = fields.type
        # Is set in the analyzer
        self.analysis: Optional[ProgramAnalysis] = None

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
            for name, func in interface.own_ghost_functions.items():
                yield name, func

    def _resources(self) -> Iterable[Tuple[str, Resource]]:
        for interface in self.interfaces.values():
            for name, resource in interface.declared_resources.items():
                yield name, resource

    @property
    def invariants(self):
        return chain(self.local_state_invariants, self.inter_contract_invariants)


class VyperInterface(VyperProgram):

    def __init__(self,
                 node: ast.Module,
                 file: str,
                 name: Optional[str],
                 config: Config,
                 functions: Dict[str, VyperFunction],
                 interfaces: Dict[str, 'VyperInterface'],
                 resources: Dict[str, Resource],
                 local_state_invariants: List[ast.Expr],
                 inter_contract_invariants: List[ast.Expr],
                 general_postconditions: List[ast.Expr],
                 transitive_postconditions: List[ast.Expr],
                 general_checks: List[ast.Expr],
                 caller_private: List[ast.Expr],
                 ghost_functions: Dict[str, GhostFunction],
                 type: InterfaceType,
                 is_stub=False):
        struct_name = f'{name}$self'
        empty_struct_type = StructType(struct_name, {})
        empty_struct = VyperStruct(struct_name, empty_struct_type, None)
        super().__init__(node,
                         file,
                         config,
                         empty_struct,
                         functions,
                         interfaces,
                         {}, {}, {},
                         resources,
                         local_state_invariants,
                         inter_contract_invariants,
                         general_postconditions,
                         transitive_postconditions,
                         general_checks,
                         {}, [], [], {})
        self.name = name
        self.imported_ghost_functions: Dict[str, List[GhostFunction]] = defaultdict(list)
        for key, value in self._ghost_functions():
            self.imported_ghost_functions[key].append(value)
        self.own_ghost_functions = ghost_functions
        self.ghost_functions: Dict[str, List[GhostFunction]] = defaultdict(list, self.imported_ghost_functions)
        for key, value in ghost_functions.items():
            self.ghost_functions[key].append(value)
        self.type = type
        self.caller_private = caller_private
        self.is_stub = is_stub

    def is_interface(self) -> bool:
        return True
