"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import List, Optional

from twovyper.ast import names
from twovyper.ast.nodes import VyperProgram, VyperFunction
from twovyper.exceptions import InvalidProgramException


def _assert(cond: bool, node: ast.AST, error_code: str):
    if not cond:
        raise InvalidProgramException(node, error_code)


def check_structure(program: VyperProgram):
    InvariantChecker(program).check()
    CheckChecker(program).check()
    PostconditionChecker(program).check()


class SpecStructureChecker(ast.NodeVisitor):

    def __init__(self, program: VyperProgram):
        self.program = program
        self.func = None

        self._inside_old = False

    def _check(self, nodes: List[ast.AST], func: Optional[VyperFunction] = None):
        self.func = func
        for node in nodes:
            self.visit(node)
        self.func

    def visit_Call(self, node: ast.Call):
        _assert(isinstance(node.func, ast.Name), node, 'spec.call')

        name = node.func.id
        # Success is of the form success() or success(if_not=cond1 or cond2 or ...)
        if name == names.SUCCESS:

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
        # Accessible is of the form accessible(to, amount, self.some_func(args...))
        elif name == names.ACCESSIBLE:
            _assert(not self._inside_old, node, 'spec.old.accessible')
            _assert(len(node.args) == 2 or len(node.args) == 3, node, 'spec.accessible')

            self.visit(node.args[0])
            self.visit(node.args[1])

            if len(node.args) == 3:
                call = node.args[2]
                _assert(isinstance(call, ast.Call), node, 'spec.accessible')
                _assert(isinstance(call.func, ast.Attribute), node, 'spec.accessible')
                _assert(isinstance(call.func.value, ast.Name), node, 'spec.accessible')
                _assert(call.func.value.id == names.SELF, node, 'spec.accessible')
                _assert(call.func.attr in self.program.functions, node, 'spec.accessible')
                _assert(call.func.attr != names.INIT, node, 'spec.accessible')

                self.generic_visit(call)
        elif name == names.OLD:
            inside_old = self._inside_old
            self._inside_old = True
            self.generic_visit(node)
            self._inside_old = inside_old
        else:
            self.generic_visit(node)


class InvariantChecker(SpecStructureChecker):

    def check(self):
        self._check(self.program.invariants)

    def visit_Name(self, node: ast.Name):
        _assert(node.id != names.MSG, node, 'invariant.msg')
        _assert(node.id != names.BLOCK, node, 'invariant.block')

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)
        _assert(node.func.id not in names.NOT_ALLOWED_IN_INVARIANT, node, 'invariant.call')


class CheckChecker(SpecStructureChecker):

    def check(self):
        self._check(self.program.general_checks)

        for func in self.program.functions.values():
            self._check(func.checks, func)

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)
        _assert(node.func.id not in names.NOT_ALLOWED_IN_CHECK, node, 'check.call')


class PostconditionChecker(SpecStructureChecker):

    def __init__(self, program: VyperProgram):
        super().__init__(program)
        self._is_transitive = False

    def check(self):
        self._check(self.program.general_postconditions)
        self._is_transitive = True
        self._check(self.program.transitive_postconditions)
        self._is_transitive = False

        for func in self.program.functions.values():
            self._check(func.postconditions, func)

    def visit_Name(self, node: ast.Name):
        if self._is_transitive:
            _assert(node.id != names.MSG, node, 'postcondition.msg')

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)

        if self._is_transitive:
            not_allowed = names.NOT_ALLOWED_IN_TRANSITIVE_POSTCONDITION
        else:
            not_allowed = names.NOT_ALLOWED_IN_POSTCONDITION

        _assert(node.func.id not in not_allowed, node, 'postcondition.call')

        if self.func and self.func.name == names.INIT:
            _assert(node.func.id != names.OLD, node, 'postcondition.init.old')
