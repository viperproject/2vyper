"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from itertools import chain

from nagini_translation.utils import flatten
from nagini_translation.ast.nodes import VyperProgram
from nagini_translation.ast import names
from nagini_translation.exceptions import InvalidProgramException


def check_structure(program: VyperProgram):
    inv_checker = InvariantChecker()
    for inv in program.invariants:
        inv_checker.check(inv)

    check_checker = CheckChecker()
    general_checks = program.general_checks
    local_checks = flatten([func.checks for func in program.functions.values()])
    for check in chain(general_checks, local_checks):
        check_checker.visit(check)

    post_checker = PostconditionChecker()
    general_posts = program.general_postconditions
    local_posts = flatten([func.postconditions for func in program.functions.values()])
    for post in chain(general_posts, local_posts):
        post_checker.visit(post)


class SpecStructureChecker(ast.NodeVisitor):

    def check(self, node: ast.AST):
        self.visit(node)

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            raise InvalidProgramException(node, 'spec.call')


class InvariantChecker(SpecStructureChecker):

    def visit_Name(self, node: ast.Name):
        if node.id == names.MSG:
            raise InvalidProgramException(node, 'invariant.msg')
        elif node.id == names.BLOCK:
            raise InvalidProgramException(node, 'invariant.block')

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)

        if node.func.id in names.NOT_ALLOWED_IN_INVARIANT:
            raise InvalidProgramException(node, 'invariant.call')


class CheckChecker(SpecStructureChecker):

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)
        if node.func.id in names.NOT_ALLOWED_IN_CHECK:
            raise InvalidProgramException(node, 'check.call')


class PostconditionChecker(SpecStructureChecker):

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)
        if node.func.id in names.NOT_ALLOWED_IN_POSTCONDITION:
            raise InvalidProgramException(node, 'postcondition.call')
