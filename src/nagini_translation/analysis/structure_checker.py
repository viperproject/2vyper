"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import List
from itertools import chain

from nagini_translation.utils import flatten
from nagini_translation.ast.nodes import VyperProgram
from nagini_translation.ast import names
from nagini_translation.exceptions import InvalidProgramException


def check_structure(program: VyperProgram):
    inv_checker = SpecCallChecker('invariant', names.NOT_ALLOWED_IN_INVARIANT)
    for inv in program.invariants:
        inv_checker.check(inv)

    check_checker = SpecCallChecker('check', names.NOT_ALLOWED_IN_CHECK)
    general_checks = program.general_checks
    local_checks = flatten([func.checks for func in program.functions.values()])
    for check in chain(general_checks, local_checks):
        check_checker.visit(check)

    post_checker = SpecCallChecker('postcondition', names.NOT_ALLOWED_IN_POSTCONDITION)
    general_posts = program.general_postconditions
    local_posts = flatten([func.postconditions for func in program.functions.values()])
    for post in chain(general_posts, local_posts):
        post_checker.visit(post)


class SpecStructureChecker(ast.NodeVisitor):

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            raise InvalidProgramException(node, 'spec.call')


class SpecCallChecker(SpecStructureChecker):

    def __init__(self, reason: str, not_allowed: List[str]):
        self.reason = reason
        self.not_allowed = not_allowed

    def check(self, node: ast.AST):
        self.visit(node)

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)
        if node.func.id in self.not_allowed:
            raise InvalidProgramException(node, f"{self.reason}.call")
