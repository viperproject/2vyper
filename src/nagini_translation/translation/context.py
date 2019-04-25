"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import contextmanager


class Context:
    
    def __init__(self, file: str):
        self.file = file
        self.invariants = []

        self.function = None
        
        self.all_vars = {}
        self.args = {}
        self.locals = {}
        self.types = {}

        self._break_label_counter = -1
        self._continue_label_counter = -1
        self.break_label = None
        self.continue_label = None

        self.result_var = None
        self.end_label = None

    def _next_break_label(self) -> str:
        self._break_label_counter += 1
        return f"break_{self._break_label_counter}"

    def _next_continue_label(self) -> str:
        self._continue_label_counter += 1
        return f"continue_{self._continue_label_counter}"


@contextmanager
def function_scope(ctx: Context):
    """
    Should be used in a ``with`` statement.
    Saves the current context state of a function, then clears it for the body
    of the ``with`` statement and restores the previous one in the end.
    """

    function = ctx.function

    all_vars = ctx.all_vars
    args = ctx.args
    locals = ctx.locals
    types = ctx.types

    _break_label_counter = ctx._break_label_counter
    _continue_label_counter = ctx._continue_label_counter
    break_label = ctx.break_label
    continue_label = ctx.continue_label

    result_var = ctx.result_var
    end_label = ctx.end_label

    ctx.function = None

    ctx.all_vars = {}
    ctx.args = {}
    ctx.locals = {}
    ctx.types = {}

    ctx._break_label_counter = -1
    ctx._continue_label_counter = -1
    ctx.break_label = None
    ctx.continue_label = None

    ctx.result_var = None
    ctx.end_label = None

    yield

    ctx.function = function

    ctx.all_vars = all_vars
    ctx.args = args
    ctx.locals = locals
    ctx.types = types

    ctx._break_label_counter = _break_label_counter
    ctx._continue_label_counter = _continue_label_counter
    ctx.break_label = break_label
    ctx.continue_label = continue_label

    ctx.result_var = result_var
    ctx.end_label = end_label


@contextmanager
def break_scope(ctx: Context):
    """
    Should be used in a ``with`` statement.
    Saves the current ``break`` target label, creates a new one for the body
    of the ``with`` statement, and restores the previous one in the end.
    """

    break_label = ctx.break_label
    ctx.break_label = ctx._next_break_label()

    yield

    ctx.break_label = break_label


@contextmanager
def continue_scope(ctx: Context):
    """
    Should be used in a ``with`` statement.
    Saves the current ``break`` target label, creates a new one for the body
    of the ``with`` statement, and restores the previous one in the end.
    """

    continue_label = ctx.continue_label
    ctx.continue_label = ctx._next_continue_label()

    yield

    ctx.continue_label = continue_label
    