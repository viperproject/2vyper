"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.nodes import VyperProgram, VyperFunction
from twovyper.ast.visitors import NodeVisitor

from twovyper.utils import first


def compute(program: VyperProgram):
    _AccessibleHeuristics().compute(program)


class _AccessibleHeuristics(NodeVisitor):

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

    def visit_FunctionCall(self, node: ast.FunctionCall):
        is_send = node.name == names.SEND
        is_rawcall = node.name == names.RAW_CALL
        is_raw_send = names.RAW_CALL_VALUE in [kw.name for kw in node.keywords]
        if is_send or (is_rawcall and is_raw_send):
            self.send_functions.append(self.current_function)

        self.generic_visit(node)
