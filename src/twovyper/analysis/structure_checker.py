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
from twovyper.exceptions import InvalidProgramException, UnsupportedException


def _assert(cond: bool, node: ast.AST, error_code: str):
    if not cond:
        raise InvalidProgramException(node, error_code)


def check_structure(program: VyperProgram):
    ProgramChecker(program).check()
    InvariantChecker(program).check()
    CheckChecker(program).check()
    PostconditionChecker(program).check()


class ProgramChecker(ast.NodeVisitor):

    def __init__(self, program: VyperProgram):
        self.program = program
        self.is_pure = False

    def check(self):
        for func in self.program.functions.values():
            if func.is_pure() and not func.is_constant():
                msg = "Pure functions must be constant."
                raise InvalidProgramException(func.node, 'pure.not.constant', msg)

            self.is_pure = func.is_pure()
            self.visit(func.node)
            self.is_pure = False

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            name = node.func.id

            if name == names.RAW_CALL:
                if names.RAW_CALL_DELEGATE_CALL in [kw.arg for kw in node.keywords]:
                    raise UnsupportedException(node, 'Delegate calls are not supported.')
        elif isinstance(node.func, ast.Attribute) and self.is_pure:
            fname = node.func.attr
            if isinstance(node.func.value, ast.Name):
                value = node.func.value.id
                is_self_pure = value == names.SELF and self.program.functions[fname].is_pure()
                if not is_self_pure:
                    raise InvalidProgramException(node, 'pure.not.pure')
            else:
                raise InvalidProgramException(node, 'pure.not.pure')

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if self.is_pure and node.id in names.NOT_ALLOWED_IN_PURE:
            raise InvalidProgramException(node, 'pure.not.pure')


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
        if isinstance(node.func, ast.Attribute):
            _assert(isinstance(node.func.value, ast.Name), node, 'spec.call')
            _assert(node.func.value.id == names.SELF, node, 'spec.call')
            _assert(self.program.functions[node.func.attr].is_pure(), node, 'spec.call')
            self.generic_visit(node)
        else:
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
        if isinstance(node.func, ast.Name):
            _assert(node.func.id not in names.NOT_ALLOWED_IN_INVARIANT, node, 'invariant.call')


class CheckChecker(SpecStructureChecker):

    def check(self):
        self._check(self.program.general_checks)

        for func in self.program.functions.values():
            self._check(func.checks, func)

    def visit_Call(self, node: ast.Call):
        super().visit_Call(node)
        if isinstance(node.func, ast.Name):
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

        if isinstance(node.func, ast.Name):
            if self._is_transitive:
                not_allowed = names.NOT_ALLOWED_IN_TRANSITIVE_POSTCONDITION
            else:
                not_allowed = names.NOT_ALLOWED_IN_POSTCONDITION

            _assert(node.func.id not in not_allowed, node, 'postcondition.call')

            if self.func and self.func.name == names.INIT:
                _assert(node.func.id != names.OLD, node, 'postcondition.init.old')
