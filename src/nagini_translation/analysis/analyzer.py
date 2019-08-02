"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.ast import names
from nagini_translation.ast.nodes import VyperProgram, VyperFunction

from nagini_translation.analysis.structure_checker import check_structure
from nagini_translation.analysis.type_annotator import TypeAnnotator


def analyze(program: VyperProgram):
    """
    Checks the program for structural errors, adds type information to all program expressions
    and creates an analysis for each function.
    """
    check_structure(program)
    TypeAnnotator(program).annotate_program()

    for function in program.functions.values():
        function.analysis = FunctionAnalysis()
        _FunctionAnalyzer(function).analyze()

    program.analysis = ProgramAnalysis()
    _ProgramAnalyzer(program).analyze()


class ProgramAnalysis:

    def __init__(self):
        pass


class FunctionAnalysis:

    def __init__(self):
        self.uses_issued = False


class _ProgramAnalyzer(ast.NodeVisitor):

    def __init__(self, program: VyperProgram):
        self.program = program

    def analyze(self):
        for post in self.program.general_postconditions:
            self.visit(post)

        for check in self.program.general_checks:
            self.visit(check)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == names.ISSUED:
            for function in self.program.functions:
                function.analysis.uses_issued = True

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
