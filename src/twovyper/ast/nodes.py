"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Dict, List, Optional

from twovyper.ast import names
from twovyper.ast.types import (
    VyperType, FunctionType, StructType, ContractType, EventType, InterfaceType
)


class VyperConfig:

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
                 local_vars: Dict[str, VyperVar],
                 type: FunctionType,
                 postconditions: List[ast.Expr],
                 checks: List[ast.Expr],
                 decorators: List[str],
                 node: Optional[ast.FunctionDef]):
        self.name = name
        self.args = args
        self.local_vars = local_vars
        self.type = type
        self.postconditions = postconditions
        self.checks = checks
        self.decorators = decorators
        self.node = node
        # Gets set in the analyzer
        self.analysis = None

    def is_public(self) -> bool:
        return names.PUBLIC in self.decorators

    def is_private(self) -> bool:
        return names.PRIVATE in self.decorators

    def is_payable(self) -> bool:
        return names.PAYABLE in self.decorators

    def is_constant(self) -> bool:
        return names.CONSTANT in self.decorators

    def is_pure(self) -> bool:
        return names.PURE in self.decorators


class VyperStruct:

    def __init__(self, name: str, type: StructType, node: ast.ClassDef):
        self.name = name
        self.type = type
        self.node = node


class VyperContract:

    def __init__(self, name: str, type: ContractType, node: ast.ClassDef):
        self.name = name
        self.type = type
        self.node = node


class VyperEvent:

    def __init__(self, name: str, type: EventType):
        self.name = name
        self.type = type


class VyperProgram:

    def __init__(self,
                 file: str,
                 config: VyperConfig,
                 fields: VyperStruct,
                 functions: Dict[str, VyperFunction],
                 interfaces: Dict[str, 'VyperProgram'],
                 structs: Dict[str, VyperStruct],
                 contracts: Dict[str, VyperContract],
                 events: Dict[str, VyperEvent],
                 invariants: List[ast.Expr],
                 general_postconditions: List[ast.Expr],
                 transitive_postconditions: List[ast.Expr],
                 general_checks: List[ast.Expr]):
        self.file = file
        self.config = config
        self.fields = fields
        self.functions = functions
        self.interfaces = interfaces
        self.structs = structs
        self.contracts = contracts
        self.events = events
        self.invariants = invariants
        self.general_postconditions = general_postconditions
        self.transitive_postconditions = transitive_postconditions
        self.general_checks = general_checks
        # Gets set in the analyzer
        self.analysis = None

    def is_interface(self) -> bool:
        return False


class VyperInterface(VyperProgram):

    def __init__(self,
                 file: str,
                 name: Optional[str],
                 config: VyperConfig,
                 functions: Dict[str, VyperFunction],
                 type: InterfaceType):
        struct_name = f'{name}$self'
        empty_struct = VyperStruct(struct_name, StructType(struct_name, {}), None)
        super().__init__(file, config, empty_struct, functions, {}, {}, {}, {}, [], [], [], [])
        self.name = name
        self.type = type

    def is_interface(self) -> bool:
        return True
