"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from twovyper.ast import names
from twovyper.ast.nodes import VyperProgram, VyperFunction

from twovyper.analysis import heuristics
from twovyper.analysis.structure_checker import check_structure
from twovyper.analysis.symbol_checker import check_symbols
from twovyper.analysis.type_annotator import TypeAnnotator

from twovyper.exceptions import UnsupportedException


def analyze(program: VyperProgram):
    """
    Checks the program for structural errors, adds type information to all program expressions
    and creates an analysis for each function.
    """
    check_structure(program)
    TypeAnnotator(program).annotate_program()
    check_symbols(program)

    for function in program.functions.values():
        function.analysis = FunctionAnalysis()
        _FunctionAnalyzer(function).analyze()

    program.analysis = ProgramAnalysis()
    # The heuristics are need for analysis, therefore do them first
    heuristics.compute(program)
    _ProgramAnalyzer(program).analyze()


class ProgramAnalysis:

    def __init__(self):
        # True if and only if issued state is accessed in top-level specifications
        self.uses_issued = False
        # The function that is used to prove accessibility if none is given
        # Is set in the heuristics computation
        # May be 'None' if the heuristics is not able to determine a suitable function
        self.accessible_function = None
        # The invariant a tag belongs to
        # Each invariant has a tag that is used in accessible so we know which invariant fails
        # if we cannot prove the accessibility
        self.inv_tags = {}
        # Maps accessible ast.Call nodes to their tag
        self.accessible_tags = {}


class FunctionAnalysis:

    def __init__(self):
        # True if and only if issued state is accessed in top-level or function specifications
        self.uses_issued = False
        # The set of tags for which accessibility needs to be proven in the function
        self.accessible_tags = set()


class _ProgramAnalyzer(ast.NodeVisitor):

    def __init__(self, program: VyperProgram):
        self.program = program
        self.tag = None

    def analyze(self):
        for tag, inv in enumerate(self.program.invariants):
            self.tag = tag
            self.program.analysis.inv_tags[tag] = inv
            self.visit(inv)

        for post in self.program.general_postconditions:
            self.visit(post)

        for post in self.program.transitive_postconditions:
            self.visit(post)

        for check in self.program.general_checks:
            self.visit(check)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id == names.ISSUED:
                self.program.analysis.uses_issued = True
                for function in self.program.functions.values():
                    function.analysis.uses_issued = True
            elif node.func.id == names.ACCESSIBLE:
                self.program.analysis.accessible_tags[node] = self.tag
                if len(node.args) == 3:
                    function_name = node.args[2].func.attr
                else:
                    if not self.program.analysis.accessible_function:
                        msg = "No matching function for acccessible could be determined."
                        raise UnsupportedException(node, msg)
                    function_name = self.program.analysis.accessible_function.name
                self.program.functions[function_name].analysis.accessible_tags.add(self.tag)

        self.generic_visit(node)


class _FunctionAnalyzer(ast.NodeVisitor):

    def __init__(self, function: VyperFunction):
        self.function = function

    def analyze(self):
        for post in self.function.postconditions:
            self.visit(post)

        for check in self.function.checks:
            self.visit(check)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == names.ISSUED:
            self.function.analysis.uses_issued = True

        self.generic_visit(node)
