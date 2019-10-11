"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from twovyper.utils import first

from twovyper.ast import names
from twovyper.ast import types
from twovyper.ast.nodes import VyperProgram, VyperFunction


def compute(program: VyperProgram):
    _AccessibleHeuristics().compute(program)


class _AccessibleHeuristics(ast.NodeVisitor):

    def __init__(self):
        self.send_functions = []
        self.current_function = None

    def compute(self, program: VyperProgram):
        for function in program.functions.values():
            self.check(function)

        def is_canditate(f: VyperFunction) -> bool:
            if not f.is_public():
                return False
            elif len(f.args) == 1:
                return first(f.args.values()).type == types.VYPER_WEI_VALUE
            else:
                return not f.args

        candidates = [f for f in self.send_functions if is_canditate(f)]

        def val(f: VyperFunction):
            name = f.name.lower()
            if name == names.WITHDRAW:
                return 0
            elif names.WITHDRAW in name:
                return 1
            else:
                return 3

        candidates = sorted(candidates, key=val)
        program.analysis.accessible_function = first(candidates)

    def check(self, function: VyperFunction):
        self.current_function = function
        self.visit(function.node)

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            self.generic_visit(node)
            return

        is_send = node.func.id == names.SEND
        is_rawcall = node.func.id == names.RAW_CALL
        is_raw_send = names.RAW_CALL_VALUE in [kw.arg for kw in node.keywords]
        if is_send or (is_rawcall and is_raw_send):
            self.send_functions.append(self.current_function)

        self.generic_visit(node)
