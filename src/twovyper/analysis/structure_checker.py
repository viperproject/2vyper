"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import contextmanager
from enum import Enum
from itertools import chain
from typing import Optional, Union

from twovyper.utils import switch
from twovyper.ast import ast_nodes as ast, names
from twovyper.ast.nodes import VyperProgram, VyperFunction
from twovyper.ast.visitors import NodeVisitor

from twovyper.exceptions import InvalidProgramException, UnsupportedException


def _assert(cond: bool, node: ast.Node, error_code: str, msg: Optional[str] = None):
    if not cond:
        raise InvalidProgramException(node, error_code, msg)


def check_structure(program: VyperProgram):
    StructureChecker().check(program)


class _Context(Enum):

    CODE = 'code'
    INVARIANT = 'invariant'
    LOOP_INVARIANT = 'loop.invariant'
    CHECK = 'check'
    POSTCONDITION = 'postcondition'
    PRECONDITION = 'precondition'
    TRANSITIVE_POSTCONDITION = 'transitive.postcondition'
    GHOST_CODE = 'ghost.code'
    GHOST_FUNCTION = 'ghost.function'
    GHOST_STATEMENT = 'ghost.statement'

    @property
    def is_specification(self):
        return self not in [_Context.CODE, _Context.GHOST_FUNCTION]

    @property
    def is_postcondition(self):
        return self in [_Context.POSTCONDITION, _Context.TRANSITIVE_POSTCONDITION]


class StructureChecker(NodeVisitor):

    def __init__(self):
        self.allowed = {
            _Context.CODE: [],
            _Context.INVARIANT: names.NOT_ALLOWED_IN_INVARIANT,
            _Context.LOOP_INVARIANT: names.NOT_ALLOWED_IN_LOOP_INVARIANT,
            _Context.CHECK: names.NOT_ALLOWED_IN_CHECK,
            _Context.POSTCONDITION: names.NOT_ALLOWED_IN_POSTCONDITION,
            _Context.PRECONDITION: names.NOT_ALLOWED_IN_PRECONDITION,
            _Context.TRANSITIVE_POSTCONDITION: names.NOT_ALLOWED_IN_TRANSITIVE_POSTCONDITION,
            _Context.GHOST_CODE: names.NOT_ALLOWED_IN_GHOST_CODE,
            _Context.GHOST_FUNCTION: names.NOT_ALLOWED_IN_GHOST_FUNCTION,
            _Context.GHOST_STATEMENT: names.NOT_ALLOWED_IN_GHOST_STATEMENT
        }

        self._inside_old = False
        self._is_pure = False
        self._non_pure_parent_description: Union[str, None] = None
        self._visited_an_event = False
        self._only_one_event_allowed = False
        self._function_pure_checker = _FunctionPureChecker()

    @contextmanager
    def _inside_old_scope(self):
        current_inside_old = self._inside_old
        self._inside_old = True

        yield

        self._inside_old = current_inside_old

    @contextmanager
    def _inside_pure_scope(self, node_description: str = None):
        is_pure = self._is_pure
        self._is_pure = True
        description = self._non_pure_parent_description
        self._non_pure_parent_description = node_description

        yield

        self._is_pure = is_pure
        self._non_pure_parent_description = description

    @contextmanager
    def _inside_one_event_scope(self):
        visited_an_event = self._visited_an_event
        self._visited_an_event = False

        only_one_event_allowed = self._only_one_event_allowed
        self._only_one_event_allowed = True

        yield

        self._visited_an_event = visited_an_event
        self._only_one_event_allowed = only_one_event_allowed

    def check(self, program: VyperProgram):
        if program.resources and not program.config.has_option(names.CONFIG_ALLOCATION):
            resource = next(iter(program.resources.values()))
            msg = "Resources require allocation config option."
            raise InvalidProgramException(resource.node, 'alloc.not.alloc', msg)

        for function in program.functions.values():
            self.visit(function.node, _Context.CODE, program, function)
            if function.is_pure():
                self._function_pure_checker.check_function(function, program)

            for postcondition in function.postconditions:
                self.visit(postcondition, _Context.POSTCONDITION, program, function)

            if function.preconditions:
                _assert(not function.is_public(), function.preconditions[0],
                        'invalid.preconditions', 'Public functions are not allowed to have preconditions.')
            for precondition in function.preconditions:
                self.visit(precondition, _Context.PRECONDITION, program, function)

            for check in function.checks:
                self.visit(check, _Context.CHECK, program, function)

            for performs in function.performs:
                self._visit_performs(performs, program, function)

        for invariant in program.invariants:
            self.visit(invariant, _Context.INVARIANT, program, None)

        for check in program.general_checks:
            self.visit(check, _Context.CHECK, program, None)

        for postcondition in program.general_postconditions:
            self.visit(postcondition, _Context.POSTCONDITION, program, None)

        for postcondition in program.transitive_postconditions:
            self.visit(postcondition, _Context.TRANSITIVE_POSTCONDITION, program, None)

        for ghost_function in program.ghost_function_implementations.values():
            self.visit(ghost_function.node, _Context.GHOST_FUNCTION, program, None)

    def visit(self, node: ast.Node, *args):
        assert len(args) == 3
        ctx, program, function = args
        _assert(ctx != _Context.GHOST_CODE or isinstance(node, ast.AllowedInGhostCode), node, 'invalid.ghost.code')
        super().visit(node, ctx, program, function)

    def _visit_performs(self, node: ast.Expr, program: VyperProgram, function: VyperFunction):
        _assert(isinstance(node, ast.FunctionCall) and node.name in names.GHOST_STATEMENTS, node, 'invalid.performs')
        self.visit(node, _Context.CODE, program, function)

    def visit_BoolOp(self, node: ast.BoolOp, *args):
        with switch(node.op) as case:
            if case(ast.BoolOperator.OR):
                with self._inside_one_event_scope():
                    with self._inside_pure_scope('disjunctions'):
                        self.generic_visit(node, *args)
            elif case(ast.BoolOperator.IMPLIES):
                with self._inside_pure_scope('(e ==> A) as the left hand side'):
                    self.visit(node.left, *args)
                self.visit(node.right, *args)
            elif case(ast.BoolOperator.AND):
                self.generic_visit(node, *args)
            else:
                assert False

    def visit_Not(self, node: ast.Not, *args):
        with self._inside_pure_scope('not expressions'):
            self.generic_visit(node, *args)

    def visit_Containment(self, node: ast.Containment, *args):
        with self._inside_pure_scope(f"containment expressions like \"{node.op}\""):
            self.generic_visit(node, *args)

    def visit_Equality(self, node: ast.Equality, *args):
        with self._inside_pure_scope('== expressions'):
            self.generic_visit(node, *args)

    def visit_IfExpr(self, node: ast.IfExpr, *args):
        self.visit(node.body, *args)
        self.visit(node.orelse, *args)
        with self._inside_pure_scope('if expressions like (A1 if e else A2)'):
            self.visit(node.test, *args)

    def visit_Dict(self, node: ast.Dict, *args):
        with self._inside_pure_scope('dicts'):
            self.generic_visit(node, *args)

    def visit_List(self, node: ast.List, *args):
        with self._inside_pure_scope('lists'):
            self.generic_visit(node, *args)

    def visit_Tuple(self, node: ast.Tuple, *args):
        with self._inside_pure_scope('tuples'):
            self.generic_visit(node, *args)

    def visit_For(self, node: ast.For, ctx: _Context, program: VyperProgram, function: Optional[VyperFunction]):
        self.generic_visit(node, ctx, program, function)
        if function:
            for loop_inv in function.loop_invariants.get(node, []):
                self.visit(loop_inv, _Context.LOOP_INVARIANT, program, function)

    def visit_FunctionDef(self, node: ast.FunctionDef, ctx: _Context,
                          program: VyperProgram, function: Optional[VyperFunction]):
        for stmt in node.body:
            if ctx == _Context.GHOST_FUNCTION:
                new_ctx = ctx
            elif ctx == _Context.CODE:
                new_ctx = _Context.GHOST_CODE if stmt.is_ghost_code else ctx
            else:
                assert False

            self.visit(stmt, new_ctx, program, function)

    @staticmethod
    def visit_Name(node: ast.Name, ctx: _Context, program: VyperProgram, function: Optional[VyperFunction]):
        if ctx == _Context.GHOST_FUNCTION and node.id in names.ENV_VARIABLES:
            _assert(node.id not in names.ENV_VARIABLES, node, 'invalid.ghost.function')
        elif ctx == _Context.INVARIANT:
            _assert(node.id != names.MSG, node, 'invariant.msg')
            _assert(node.id != names.BLOCK, node, 'invariant.block')
        elif ctx == _Context.TRANSITIVE_POSTCONDITION:
            _assert(node.id != names.MSG, node, 'postcondition.msg')

    def visit_FunctionCall(self, node: ast.FunctionCall, ctx: _Context,
                           program: VyperProgram, function: Optional[VyperFunction]):
        _assert(node.name not in self.allowed[ctx], node, f'{ctx.value}.call')

        if ctx == _Context.POSTCONDITION and function and function.name == names.INIT:
            _assert(node.name != names.OLD, node, 'postcondition.init.old')

        if function and node.name == names.PUBLIC_OLD:
            if ctx == _Context.POSTCONDITION:
                _assert(function.is_private(), node, 'postcondition.public.old')
            elif ctx == _Context.PRECONDITION:
                _assert(function.is_private(), node, 'precondition.public.old')

        if function and node.name == names.EVENT:
            if ctx == _Context.POSTCONDITION:
                _assert(function.is_private(), node, 'postcondition.event')
            elif ctx == _Context.PRECONDITION:
                _assert(function.is_private(), node, 'precondition.event')

        if node.name == names.EVENT:
            if ctx == _Context.PRECONDITION \
                    or ctx == _Context.POSTCONDITION \
                    or ctx == _Context.LOOP_INVARIANT:
                _assert(not self._is_pure, node, 'spec.event',
                        "Events are only in checks pure expressions. "
                        f"They cannot be used in {self._non_pure_parent_description}.")
            if self._only_one_event_allowed:
                _assert(not self._visited_an_event, node, 'spec.event',
                        'In this context only one event expression is allowed.')
            self._visited_an_event = True

        elif node.name == names.IMPLIES:
            with self._inside_pure_scope('implies(e, A) as the expression "e"'):
                self.visit(node.args[0], ctx, program, function)
            self.visit(node.args[1], ctx, program, function)

        # Success is of the form success() or success(if_not=cond1 or cond2 or ...)
        elif node.name == names.SUCCESS:

            def check_success_args(arg: ast.Node):
                if isinstance(arg, ast.Name):
                    _assert(arg.id in names.SUCCESS_CONDITIONS, arg, 'spec.success')
                elif isinstance(arg, ast.BoolOp) and arg.op == ast.BoolOperator.OR:
                    check_success_args(arg.left)
                    check_success_args(arg.right)
                else:
                    raise InvalidProgramException(arg, 'spec.success')

            _assert(len(node.keywords) <= 1, node, 'spec.success')
            if node.keywords:
                _assert(node.keywords[0].name == names.SUCCESS_IF_NOT, node, 'spec.success')
                check_success_args(node.keywords[0].value)

            if len(node.keywords) == 0 and len(node.args) == 1:
                argument = node.args[0]
                _assert(isinstance(argument, ast.ReceiverCall), node, 'spec.success')
                assert isinstance(argument, ast.ReceiverCall)
                func = program.functions.get(argument.name)
                _assert(func is not None, argument, 'spec.success',
                        'Only functions defined in this contract can be called from the specification.')
                _assert(func.is_pure(), argument, 'spec.success',
                        'Only pure functions can be called from the specification.')
                self.generic_visit(argument, ctx, program, function)

            return
        # Accessible is of the form accessible(to, amount, self.some_func(args...))
        elif node.name == names.ACCESSIBLE:
            _assert(not self._inside_old, node, 'spec.old.accessible')
            _assert(len(node.args) == 2 or len(node.args) == 3, node, 'spec.accessible')

            self.visit(node.args[0], ctx, program, function)
            self.visit(node.args[1], ctx, program, function)

            if len(node.args) == 3:
                call = node.args[2]
                _assert(isinstance(call, ast.ReceiverCall), node, 'spec.accessible')
                assert isinstance(call, ast.ReceiverCall)
                _assert(isinstance(call.receiver, ast.Name), node, 'spec.accessible')
                _assert(call.receiver.id == names.SELF, node, 'spec.accessible')
                _assert(call.name in program.functions, node, 'spec.accessible')
                _assert(program.functions[call.name].is_public(), node, 'spec.accessible',
                        "Only public functions may be used in an accessible expression")
                _assert(call.name != names.INIT, node, 'spec.accessible')

                self.generic_visit(call, ctx, program, function)

            return
        elif node.name in [names.FORALL, names.FOREACH]:
            _assert(len(node.args) >= 2 and not node.keywords, node, 'invalid.no.args')
            first_arg = node.args[0]
            _assert(isinstance(first_arg, ast.Dict), node.args[0], f'invalid.{node.name}')

            assert isinstance(first_arg, ast.Dict)
            for name in first_arg.keys:
                _assert(isinstance(name, ast.Name), name, f'invalid.{node.name}')

            for trigger in node.args[1:len(node.args) - 1]:
                _assert(isinstance(trigger, ast.Set), trigger, f'invalid.{node.name}')
                self.visit(trigger, ctx, program, function)

            body = node.args[-1]

            if node.name == names.FOREACH:
                _assert(isinstance(body, ast.FunctionCall), body, 'invalid.foreach')
                assert isinstance(body, ast.FunctionCall)
                _assert(body.name in names.QUANTIFIED_GHOST_STATEMENTS, body, 'invalid.foreach')

            self.visit(body, ctx, program, function)
            return
        elif node.name in [names.OLD, names.PUBLIC_OLD]:
            with self._inside_old_scope():
                self.generic_visit(node, ctx, program, function)

            return
        elif node.name == names.RESULT or node.name == names.REVERT:
            if len(node.args) == 1:
                argument = node.args[0]
                _assert(isinstance(argument, ast.ReceiverCall), node, f"spec.{node.name}")
                assert isinstance(argument, ast.ReceiverCall)
                func = program.functions.get(argument.name)
                _assert(func is not None, argument, f"spec.{node.name}",
                        'Only functions defined in this contract can be called from the specification.')
                _assert(func.is_pure(), argument, f"spec.{node.name}",
                        'Only pure functions can be called from the specification.')
                self.generic_visit(argument, ctx, program, function)

                return

        elif node.name == names.INDEPENDENT:
            with self._inside_pure_scope('independent expressions'):
                self.visit(node.args[0], ctx, program, function)

            def check_allowed(arg):
                if isinstance(arg, ast.FunctionCall):
                    is_old = len(arg.args) == 1 and arg.name in [names.OLD, names.PUBLIC_OLD]
                    _assert(is_old, node, 'spec.independent')
                    return check_allowed(arg.args[0])
                if isinstance(arg, ast.Attribute):
                    return check_allowed(arg.value)
                elif isinstance(arg, ast.Name):
                    allowed = [names.SELF, names.BLOCK, names.CHAIN, names.TX, *function.args]
                    _assert(arg.id in allowed, node, 'spec.independent')
                else:
                    _assert(False, node, 'spec.independent')

            check_allowed(node.args[1])
        elif node.name == names.RAW_CALL:
            if names.RAW_CALL_DELEGATE_CALL in (kw.name for kw in node.keywords):
                raise UnsupportedException(node, "Delegate calls are not supported.")
        elif node.name == names.PREVIOUS or node.name == names.LOOP_ARRAY or node.name == names.LOOP_ITERATION:
            if len(node.args) > 0:
                _assert(isinstance(node.args[0], ast.Name), node.args[0], f"invalid.{node.name}")
        elif node.name == names.RANGE:
            if len(node.args) == 1:
                _assert(isinstance(node.args[0], ast.Num), node.args[0], 'invalid.range',
                        'The range operator should be of the form: range(const). '
                        '"const" must be a constant integer expression.')
            elif len(node.args) == 2:
                first_arg = node.args[0]
                second_arg = node.args[1]
                msg = 'The range operator should be of the form: range(const1, const2) or range(x, x + const1). '\
                      '"const1" and "const2" must be constant integer expressions.'
                if isinstance(second_arg, ast.ArithmeticOp) \
                        and second_arg.op == ast.ArithmeticOperator.ADD \
                        and ast.compare_nodes(first_arg, second_arg.left):
                    _assert(isinstance(second_arg.right, ast.Num), second_arg.right, 'invalid.range', msg)
                else:
                    _assert(isinstance(first_arg, ast.Num), first_arg, 'invalid.range', msg)
                    _assert(isinstance(second_arg, ast.Num), second_arg, 'invalid.range', msg)
                    assert isinstance(first_arg, ast.Num) and isinstance(second_arg, ast.Num)
                    _assert(first_arg.n < second_arg.n, node, 'invalid.range',
                            'The range operator should be of the form: range(const1, const2). '
                            '"const2" must be greater than "const1".')

        if node.name in names.ALLOCATION_FUNCTIONS:
            msg = "Allocation statements require allocation config option."
            _assert(program.config.has_option(names.CONFIG_ALLOCATION), node, 'alloc.not.alloc', msg)

        if node.name in names.GHOST_STATEMENTS:
            msg = "Allocation statements are not allowed in constant functions."
            _assert(not (function and function.is_constant()), node, 'alloc.in.constant', msg)

        arg_ctx = _Context.GHOST_STATEMENT if node.name in names.GHOST_STATEMENTS else ctx

        if node.resource:
            # Resources are only allowed in allocation functions. They can have the following structure:
            #   - a simple name: r
            #   - an exchange: r <-> s
            #   - a creator: creator(r)

            _assert(node.name in names.ALLOCATION_FUNCTIONS, node, 'invalid.no.resources')

            def check_resource(resource: ast.Node, top: bool):
                if isinstance(resource, ast.Name):
                    return
                elif isinstance(resource, ast.Exchange) and top:
                    check_resource(resource.left, False)
                    check_resource(resource.right, False)
                elif isinstance(resource, ast.FunctionCall):
                    if resource.name == names.CREATOR:
                        _assert(len(resource.args) == 1 and not resource.keywords, resource, 'invalid.resource')
                        check_resource(resource.args[0], False)
                    else:
                        self.generic_visit(resource, arg_ctx, program, function)
                else:
                    _assert(False, resource, 'invalid.resource')

            check_resource(node.resource, True)
        else:
            self.visit_nodes(chain(node.args, node.keywords), arg_ctx, program, function)

    def visit_ReceiverCall(self, node: ast.ReceiverCall, ctx: _Context,
                           program: VyperProgram, function: Optional[VyperFunction]):
        if ctx == _Context.GHOST_CODE:
            _assert(False, node, 'invalid.ghost.code')
        elif ctx.is_specification:
            _assert(False, node, 'spec.call')
        elif ctx == _Context.GHOST_FUNCTION:
            _assert(False, node, 'invalid.ghost')

        self.generic_visit(node, ctx, program, function)

    def visit_Exchange(self, node: ast.Exchange, ctx: _Context,
                       program: VyperProgram, function: Optional[VyperFunction]):
        _assert(False, node, 'exchange.not.resource')

        self.generic_visit(node, ctx, program, function)

    @staticmethod
    def _visit_assertion(node: Union[ast.Assert, ast.Raise], ctx: _Context):
        if ctx == _Context.GHOST_CODE:
            _assert(node.msg and isinstance(node.msg, ast.Name), node, 'invalid.ghost.code')
            _assert(node.msg.id == names.UNREACHABLE, node, 'invalid.ghost.code')

    def visit_Assert(self, node: ast.Assert, ctx: _Context, program: VyperProgram, function: Optional[VyperFunction]):
        self._visit_assertion(node, ctx)
        self.generic_visit(node, ctx, program, function)

    def visit_Raise(self, node: ast.Raise, ctx: _Context, program: VyperProgram, function: Optional[VyperFunction]):
        self._visit_assertion(node, ctx)
        self.generic_visit(node, ctx, program, function)


class _FunctionPureChecker(NodeVisitor):
    """
    Checks if a given VyperFunction is pure
    """

    def check_function(self, function: VyperFunction, program: VyperProgram):
        # A function must be constant, private and non-payable to be valid
        if not (function.is_constant() and function.is_private() and (not function.is_payable())):
            _assert(False, function.node, 'invalid.pure', 'A pure function must be constant, private and non-payable')
        elif not function.type.return_type:
            _assert(False, function.node, 'invalid.pure', 'A pure function must have a return type')
        else:
            # Check checks
            if function.checks:
                _assert(False, function.checks[0], 'invalid.pure',
                        'A pure function must not have checks')
            # Check performs
            if function.performs:
                _assert(False, function.performs[0], 'invalid.pure',
                        'A pure function must not have performs')
            # Check preconditions
            if function.preconditions:
                _assert(False, function.preconditions[0], 'invalid.pure',
                        'A pure function must not have preconditions')
            # Check postconditions
            if function.postconditions:
                _assert(False, function.postconditions[0], 'invalid.pure',
                        'A pure function must not have postconditions')
            # Check Code
            self.visit(function.node, program)

    def visit_Name(self, node: ast.Name, program: VyperProgram):
        with switch(node.id) as case:
            if case(names.MSG) \
                    or case(names.BLOCK) \
                    or case(names.TX):
                _assert(False, node, 'invalid.pure', 'Pure functions are not allowed to use "msg", "block" or "tx".')
        self.generic_visit(node, program)

    def visit_ExprStmt(self, node: ast.ExprStmt, program: VyperProgram):
        # A call to clear is an assignment, all other expressions are not valid.
        if isinstance(node.value, ast.FunctionCall) and node.value.name == names.CLEAR:
            self.generic_visit(node, program)
        else:
            _assert(False, node, 'invalid.pure', 'Pure functions are not allowed to have just an expression as a '
                                                 'statement,  since expressions must not have side effects.')

    def visit_FunctionCall(self, node: ast.FunctionCall, program: VyperProgram):
        with switch(node.name) as case:
            if (
                    # Vyper functions with side effects
                    case(names.RAW_LOG)
                    # Specification functions with side effects
                    or case(names.ACCESSIBLE)
                    or case(names.INDEPENDENT)
                    or case(names.REORDER_INDEPENDENT)
                    # Specification functions that cannot be translated to viper functions
                    # but are also not necessary
                    or case(names.EVENT)
                    or case(names.OLD)
                    or case(names.ISSUED)
                    or case(names.PUBLIC_OLD)
            ):
                _assert(False, node, 'invalid.pure',
                        f'Only functions without side effects may be used in pure functions ("{node.name}" is invalid)')
            else:
                self.generic_visit(node, program)

    def visit_ReceiverCall(self, node: ast.ReceiverCall, program: VyperProgram):
        with switch(node.receiver.id) as case:
            if case(names.SELF):
                self.generic_visit(node, program)
                _assert(program.functions[node.name].is_pure(), node, 'invalid.pure',
                        'Pure function may only call other pure functions')
            elif case(names.LOG):
                _assert(False, node, 'invalid.pure',
                        'Pure function may not log events.')
            else:
                _assert(False, node, 'invalid.pure',
                        'Pure function must not call functions of another contract.')
