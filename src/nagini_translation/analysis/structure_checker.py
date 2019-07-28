"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from itertools import chain

from nagini_translation.ast import names
from nagini_translation.ast.nodes import VyperProgram
from nagini_translation.exceptions import InvalidProgramException
from nagini_translation.utils import flatten


def _assert(cond: bool, node: ast.AST, error_code: str):
    if not cond:
        raise InvalidProgramException(node, error_code)


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
        _assert(isinstance(node.func, ast.Name), node, 'spec.call')

        if node.func.id == names.SUCCESS:

            def check_success_args(node):
                if isinstance(node, ast.Name):
                    _assert(node.id in names.SUCCESS_CONDITIONS, node, 'spec.success')
                elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                    for val in node.values:
                        check_success_args(val)
                else:
                    raise InvalidProgramException(node, 'spec.success')

            _assert(len(node.keywords) <= 1, node, 'spec.success')
            if node.keywords:
                _assert(node.keywords[0].arg == names.SUCCESS_IF_NOT, node, 'spec.success')
                check_success_args(node.keywords[0].value)


class InvariantChecker(SpecStructureChecker):

    def visit_Name(self, node: ast.Name):
        _assert(node.id != names.MSG, node, 'invariant.msg')
        _assert(node.id != names.BLOCK, node, 'invariant.block')

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)
        _assert(node.func.id not in names.NOT_ALLOWED_IN_INVARIANT, node, 'invariant.call')


class CheckChecker(SpecStructureChecker):

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)
        _assert(node.func.id not in names.NOT_ALLOWED_IN_CHECK, node, 'check.call')


class PostconditionChecker(SpecStructureChecker):

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)
        _assert(node.func.id not in names.NOT_ALLOWED_IN_POSTCONDITION, node, 'postcondition.call')
