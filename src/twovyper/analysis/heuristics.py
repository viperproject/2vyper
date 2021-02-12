"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.nodes import VyperProgram, VyperFunction
from twovyper.ast.visitors import NodeVisitor

from twovyper.utils import first


def compute(program: VyperProgram):
    _AccessibleHeuristics().compute(program)


class _AccessibleHeuristics(NodeVisitor):

    def compute(self, program: VyperProgram):
        send_functions = []

        for function in program.functions.values():
            self.visit(function.node, function, send_functions)

        def is_canditate(f: VyperFunction) -> bool:
            if not f.is_public():
                return False
            elif len(f.args) == 1:
                return first(f.args.values()).type == types.VYPER_WEI_VALUE
            else:
                return not f.args

        def val(f: VyperFunction):
            name = f.name.lower()
            if name == names.WITHDRAW:
                return 0
            elif names.WITHDRAW in name:
                return 1
            else:
                return 3

        candidates = sorted((f for f in send_functions if is_canditate(f)), key=val)
        program.analysis.accessible_function = first(candidates)

    def visit_FunctionCall(self, node: ast.FunctionCall, function: VyperFunction, send_functions: List[VyperFunction]):
        is_send = node.name == names.SEND
        is_rawcall = node.name == names.RAW_CALL
        is_raw_send = names.RAW_CALL_VALUE in [kw.name for kw in node.keywords]
        if is_send or (is_rawcall and is_raw_send):
            send_functions.append(function)

        self.generic_visit(node, function, send_functions)
