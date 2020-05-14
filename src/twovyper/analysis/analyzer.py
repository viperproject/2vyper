"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import contextmanager
from typing import Set, Dict, List

from twovyper.ast import ast_nodes as ast, names
from twovyper.ast.nodes import VyperProgram, VyperFunction
from twovyper.ast.visitors import NodeVisitor

from twovyper.analysis import heuristics
from twovyper.analysis.structure_checker import check_structure
from twovyper.analysis.symbol_checker import check_symbols
from twovyper.analysis.type_annotator import TypeAnnotator

from twovyper.exceptions import UnsupportedException
from twovyper.utils import switch


def analyze(program: VyperProgram):
    """
    Checks the program for structural errors, adds type information to all program expressions
    and creates an analysis for each function.
    """
    check_structure(program)
    TypeAnnotator(program).annotate_program()
    check_symbols(program)

    function_analyzer = _FunctionAnalyzer()
    program_analyzer = _ProgramAnalyzer()
    invariant_analyzer = _InvariantAnalyzer()

    for function in program.functions.values():
        function.analysis = FunctionAnalysis()
        function_analyzer.analyze(function)

    program.analysis = ProgramAnalysis()
    # The heuristics are need for analysis, therefore do them first
    heuristics.compute(program)
    program_analyzer.analyze(program)
    invariant_analyzer.analyze(program)


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
        # Maps accessible ast.ReceiverCall nodes to their tag
        self.accessible_tags = {}
        # All invariants that contain allocated
        self.allocated_invariants = []


class FunctionAnalysis:

    def __init__(self):
        # True if and only if issued state is accessed in top-level or function specifications
        self.uses_issued = False
        # The set of tags for which accessibility needs to be proven in the function
        self.accessible_tags = set()
        # The set of variable names which get changed by a loop
        self.loop_used_variables: Dict[str, List[str]] = {}


class _ProgramAnalyzer(NodeVisitor):

    def analyze(self, program: VyperProgram):
        self.visit_nodes(program.invariants, program)
        self.visit_nodes(program.general_postconditions, program)
        self.visit_nodes(program.transitive_postconditions, program)
        self.visit_nodes(program.general_checks, program)

    def visit_FunctionCall(self, node: ast.FunctionCall, program: VyperProgram):
        if node.name == names.ISSUED:
            program.analysis.uses_issued = True
            for function in program.functions.values():
                function.analysis.uses_issued = True

        self.generic_visit(node, program)


class _InvariantAnalyzer(NodeVisitor):

    def analyze(self, program: VyperProgram):
        for tag, inv in enumerate(program.invariants):
            program.analysis.inv_tags[tag] = inv
            self.visit(inv, program, inv, tag)

    def visit_FunctionCall(self, node: ast.FunctionCall, program: VyperProgram, inv: ast.Expr, tag: int):
        if node.name == names.ALLOCATED:
            program.analysis.allocated_invariants.append(inv)
            return
        elif node.name == names.ACCESSIBLE:
            program.analysis.accessible_tags[node] = tag
            if len(node.args) == 3:
                function_name = node.args[2].name
            else:
                if not program.analysis.accessible_function:
                    msg = "No matching function for accessible could be determined."
                    raise UnsupportedException(node, msg)
                function_name = program.analysis.accessible_function.name
            program.functions[function_name].analysis.accessible_tags.add(tag)

        self.generic_visit(node, program, inv, tag)


class _FunctionAnalyzer(NodeVisitor):

    def __init__(self):
        super().__init__()
        self.inside_loop = False
        self.used_variables: Set[str] = set()

    @contextmanager
    def _loop_scope(self):
        used_variables = self.used_variables
        inside_loop = self.inside_loop

        self.used_variables = set()
        self.inside_loop = True

        yield

        if inside_loop:
            for name in used_variables:
                self.used_variables.add(name)
        else:
            self.used_variables = used_variables
        self.inside_loop = inside_loop

    def analyze(self, function: VyperFunction):
        self.visit_nodes(function.postconditions, function)
        self.visit_nodes(function.preconditions, function)
        self.visit_nodes(function.checks, function)
        self.generic_visit(function.node, function)

    def visit_FunctionCall(self, node: ast.FunctionCall, function: VyperFunction):
        if node.name == names.ISSUED:
            function.analysis.uses_issued = True

        self.generic_visit(node, function)

    def visit_For(self, node: ast.For, function: VyperFunction):
        with self._loop_scope():
            self.generic_visit(node, function)
            function.analysis.loop_used_variables[node.target.id] = list(self.used_variables)
        self.visit_nodes(function.loop_invariants.get(node, []), function)

    def visit_Name(self, node: ast.Name, function: VyperFunction):
        if self.inside_loop:
            with switch(node.id) as case:
                if case(names.MSG)\
                        or case(names.BLOCK)\
                        or case(names.CHAIN)\
                        or case(names.TX):
                    pass
                else:
                    self.used_variables.add(node.id)
        self.generic_visit(node, function)
