"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Optional

from twovyper.ast import ast_nodes as ast, names
from twovyper.ast.nodes import VyperProgram, VyperFunction
from twovyper.ast.visitors import NodeVisitor

from twovyper.exceptions import InvalidProgramException, UnsupportedException


def _assert(cond: bool, node: ast.Node, error_code: str):
    if not cond:
        raise InvalidProgramException(node, error_code)


def check_structure(program: VyperProgram):
    ProgramChecker(program).check()
    GhostFunctionChecker(program).check()
    InvariantChecker(program).check()
    CheckChecker(program).check()
    PostconditionChecker(program).check()


class ProgramChecker(NodeVisitor):

    def __init__(self, program: VyperProgram):
        self.program = program
        self.function = None

    def check(self):
        for func in self.program.functions.values():
            self.function = func
            self.visit(func.node)
            self.function = None

    def visit_FunctionCall(self, node: ast.FunctionCall):
        if node.name == names.RAW_CALL:
            if names.RAW_CALL_DELEGATE_CALL in [kw.name for kw in node.keywords]:
                raise UnsupportedException(node, 'Delegate calls are not supported.')

        if node.name in names.GHOST_STATEMENTS:
            if not self.program.config.has_option(names.CONFIG_ALLOCATION):
                msg = "Allocation statements require allocation config option."
                raise InvalidProgramException(node, 'alloc.not.alloc', msg)
            elif self.function.is_constant():
                msg = "Allocation statements are not allowed in constant functions."
                raise InvalidProgramException(node, 'alloc.in.constant', msg)

        self.generic_visit(node)


class GhostFunctionChecker(NodeVisitor):

    def __init__(self, program: VyperProgram):
        self.program = program

    def check(self):
        for func in self.program.ghost_function_implementations.values():
            self.visit(func.node)

    def visit_Name(self, node: ast.Name):
        if node.id in names.ENV_VARIABLES:
            raise InvalidProgramException(node, 'invalid.ghost')

    def visit_FunctionCall(self, node: ast.FunctionCall):
        if node.name in names.NOT_ALLOWED_IN_GHOST_FUNCTION:
            raise InvalidProgramException(node, 'invalid.ghost')

    def visit_ReceiverCall(self, node: ast.ReceiverCall):
        raise InvalidProgramException(node, 'invalid.ghost')


class SpecStructureChecker(NodeVisitor):

    def __init__(self, program: VyperProgram):
        self.program = program
        self.func = None

        self._inside_old = False

    def _check(self, nodes: List[ast.Node], func: Optional[VyperFunction] = None):
        self.func = func
        for node in nodes:
            self.visit(node)
        self.func

    def visit_FunctionCall(self, node: ast.FunctionCall):
        # Success is of the form success() or success(if_not=cond1 or cond2 or ...)
        if node.name == names.SUCCESS:

            def check_success_args(node):
                if isinstance(node, ast.Name):
                    _assert(node.id in names.SUCCESS_CONDITIONS, node, 'spec.success')
                elif isinstance(node, ast.BoolOp) and node.op == ast.BoolOperator.OR:
                    check_success_args(node.left)
                    check_success_args(node.right)
                else:
                    raise InvalidProgramException(node, 'spec.success')

            _assert(len(node.keywords) <= 1, node, 'spec.success')
            if node.keywords:
                _assert(node.keywords[0].name == names.SUCCESS_IF_NOT, node, 'spec.success')
                check_success_args(node.keywords[0].value)
        # Accessible is of the form accessible(to, amount, self.some_func(args...))
        elif node.name == names.ACCESSIBLE:
            _assert(not self._inside_old, node, 'spec.old.accessible')
            _assert(len(node.args) == 2 or len(node.args) == 3, node, 'spec.accessible')

            self.visit(node.args[0])
            self.visit(node.args[1])

            if len(node.args) == 3:
                call = node.args[2]
                _assert(isinstance(call, ast.ReceiverCall), node, 'spec.accessible')
                _assert(isinstance(call.receiver, ast.Name), node, 'spec.accessible')
                _assert(call.receiver.id == names.SELF, node, 'spec.accessible')
                _assert(call.name in self.program.functions, node, 'spec.accessible')
                _assert(call.name != names.INIT, node, 'spec.accessible')

                self.generic_visit(call)
        elif node.name == names.OLD:
            inside_old = self._inside_old
            self._inside_old = True
            self.generic_visit(node)
            self._inside_old = inside_old
        elif node.name == names.INDEPENDENT:
            self.visit(node.args[0])

            def check_allowed(arg):
                if isinstance(arg, ast.FunctionCall):
                    is_old = len(arg.args) == 1 and arg.name == names.OLD
                    _assert(is_old, node, 'spec.independent')
                    return check_allowed(arg.args[0])
                if isinstance(arg, ast.Attribute):
                    return check_allowed(arg.value)
                elif isinstance(arg, ast.Name):
                    _assert(arg.id in [names.SELF, names.BLOCK, names.CHAIN, names.TX, *self.func.args], node, 'spec.independent')
                else:
                    _assert(False, node, 'spec.independent')

            check_allowed(node.args[1])
        else:
            self.generic_visit(node)

    def visit_ReceiverCall(self, node: ast.ReceiverCall):
        _assert(False, node, 'spec.call')


class InvariantChecker(SpecStructureChecker):

    def check(self):
        self._check(self.program.invariants)

    def visit_Name(self, node: ast.Name):
        _assert(node.id != names.MSG, node, 'invariant.msg')
        _assert(node.id != names.BLOCK, node, 'invariant.block')

    def visit_FunctionCall(self, node: ast.FunctionCall):
        super().visit_FunctionCall(node)
        _assert(node.name not in names.NOT_ALLOWED_IN_INVARIANT, node, 'invariant.call')


class CheckChecker(SpecStructureChecker):

    def check(self):
        self._check(self.program.general_checks)

        for func in self.program.functions.values():
            self._check(func.checks, func)

    def visit_FunctionCall(self, node: ast.FunctionCall):
        super().visit_FunctionCall(node)
        _assert(node.name not in names.NOT_ALLOWED_IN_CHECK, node, 'check.call')


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

    def visit_FunctionCall(self, node: ast.FunctionCall):
        super().visit_FunctionCall(node)

        if self._is_transitive:
            not_allowed = names.NOT_ALLOWED_IN_TRANSITIVE_POSTCONDITION
        else:
            not_allowed = names.NOT_ALLOWED_IN_POSTCONDITION

        _assert(node.name not in not_allowed, node, 'postcondition.call')

        if self.func and self.func.name == names.INIT:
            _assert(node.name != names.OLD, node, 'postcondition.init.old')
