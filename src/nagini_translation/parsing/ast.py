"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Dict, List
from nagini_translation.parsing.types import VyperType


class VyperVar:

    def __init__(self, name: str, type: VyperType, node):
        self.name = name
        self.type = type
        self.node = node


class VyperFunction:

    def __init__(self, name: str, 
                       args: Dict[str, VyperVar], 
                       local_vars: Dict[str, VyperVar], 
                       ret: VyperType, 
                       preconditions: List[ast.Expr],
                       postconditions: List[ast.Expr],
                       is_public: bool,
                       node: ast.FunctionDef):
        self.name = name
        self.args = args
        self.local_vars = local_vars
        self.ret = ret
        self.preconditions = preconditions
        self.postconditions = postconditions
        self.node = node


class VyperProgram:

    def __init__(self, state: Dict[str, VyperVar], 
                       functions: Dict[str, VyperFunction], 
                       invariants: List[ast.Expr]):
        self.state = state
        self.functions = functions
        self.invariants = invariants