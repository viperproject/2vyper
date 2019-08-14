"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Dict, List, Optional

from nagini_translation.ast.types import VyperType, FunctionType, StructType, EventType


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
        return 'public' in self.decorators

    def is_payable(self) -> bool:
        return 'payable' in self.decorators


class VyperStruct:

    def __init__(self, name: str, type: StructType, node: ast.ClassDef):
        self.name = name
        self.type = type


class VyperEvent:

    def __init__(self, name: str, type: EventType):
        self.name = name
        self.type = type


class VyperProgram:

    def __init__(self,
                 config: VyperConfig,
                 fields: VyperStruct,
                 functions: Dict[str, VyperFunction],
                 structs: Dict[str, VyperStruct],
                 events: Dict[str, VyperEvent],
                 invariants: List[ast.Expr],
                 general_postconditions: List[ast.Expr],
                 general_checks: List[ast.Expr]):
        self.config = config
        self.fields = fields
        self.functions = functions
        self.structs = structs
        self.events = events
        self.invariants = invariants
        self.general_postconditions = general_postconditions
        self.general_checks = general_checks
        # Gets set in the analyzer
        self.analysis = None
