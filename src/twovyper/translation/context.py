"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import contextmanager

from twovyper.ast import names
from twovyper.translation import mangled


class Context:

    def __init__(self):
        self.file = None
        self.program = None
        # The translated types of all fields
        self.field_types = {}
        # Invariants that are known to be true and therefore don't need to be checked
        self.unchecked_invariants = []

        self.function = None

        self.all_vars = {}
        self.args = {}
        self.locals = {}
        self.quantified_vars = {}

        self._break_label_counter = -1
        self._continue_label_counter = -1
        self.break_label = None
        self.continue_label = None

        self.success_var = None
        self.revert_label = None
        self.result_var = None
        self.return_label = None

        self.inside_trigger = False

        self._local_var_counter = -1
        self.new_local_vars = []

        self._quantified_var_counter = -1
        self._inline_counter = -1
        self._current_inline = -1

    @property
    def self_type(self):
        return self.program.fields.type

    @property
    def self_var(self):
        return self.all_vars[names.SELF]

    @property
    def old_self_var(self):
        return self.all_vars[mangled.OLD_SELF]

    @property
    def pre_self_var(self):
        return self.all_vars[mangled.PRE_SELF]

    @property
    def issued_self_var(self):
        return self.all_vars[mangled.ISSUED_SELF]

    @property
    def msg_var(self):
        return self.all_vars[names.MSG]

    @property
    def block_var(self):
        return self.all_vars[names.BLOCK]

    @property
    def tx_var(self):
        return self.all_vars[names.TX]

    def new_local_var_name(self, name: str = 'local') -> str:
        self._local_var_counter += 1
        return f'${name}_{self._local_var_counter}'

    def new_quantified_var_name(self) -> str:
        self._quantified_var_counter += 1
        return f'$q{self._quantified_var_counter}'

    @property
    def inline_prefix(self) -> str:
        if self._current_inline == -1:
            return ''
        else:
            return f'i{self._current_inline}$'

    def _next_break_label(self) -> str:
        self._break_label_counter += 1
        return f'break_{self._break_label_counter}'

    def _next_continue_label(self) -> str:
        self._continue_label_counter += 1
        return f'continue_{self._continue_label_counter}'


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
    quantified_vars = ctx.quantified_vars

    _break_label_counter = ctx._break_label_counter
    _continue_label_counter = ctx._continue_label_counter
    break_label = ctx.break_label
    continue_label = ctx.continue_label

    success_var = ctx.success_var
    revert_label = ctx.revert_label
    result_var = ctx.result_var
    return_label = ctx.return_label

    inside_trigger = ctx.inside_trigger

    local_var_counter = ctx._local_var_counter
    new_local_vars = ctx.new_local_vars

    quantified_var_counter = ctx._quantified_var_counter
    inline_counter = ctx._inline_counter
    current_inline = ctx._current_inline

    ctx.function = None

    ctx.all_vars = {}
    ctx.args = {}
    ctx.locals = {}
    ctx.quantified_vars = {}

    ctx._break_label_counter = -1
    ctx._continue_label_counter = -1
    ctx.break_label = None
    ctx.continue_label = None

    ctx.success_var = None
    ctx.revert_label = None
    ctx.result_var = None
    ctx.return_label = None

    ctx.inside_trigger = False

    ctx._local_var_counter = -1
    ctx.new_local_vars = []

    ctx._quantified_var_counter = -1
    ctx._inline_counter = -1
    ctx._current_inline = -1

    yield

    ctx.function = function

    ctx.all_vars = all_vars
    ctx.args = args
    ctx.locals = locals
    ctx.quantified_vars = quantified_vars

    ctx._break_label_counter = _break_label_counter
    ctx._continue_label_counter = _continue_label_counter
    ctx.break_label = break_label
    ctx.continue_label = continue_label

    ctx.success_var = success_var
    ctx.revert_label = revert_label
    ctx.result_var = result_var
    ctx.return_label = return_label

    ctx.inside_trigger = inside_trigger

    ctx._local_var_counter = local_var_counter
    ctx.new_local_vars = new_local_vars

    ctx._quantified_var_counter = quantified_var_counter
    ctx._inline_counter = inline_counter
    ctx._current_inline = current_inline


@contextmanager
def quantified_var_scope(ctx: Context):
    all_vars = ctx.all_vars.copy()
    quantified_vars = ctx.quantified_vars.copy()
    quantified_var_counter = ctx._quantified_var_counter
    ctx.quantified_var_counter = -1

    yield

    ctx.all_vars = all_vars
    ctx.quantified_vars = quantified_vars
    ctx._quantified_var_counter = quantified_var_counter


@contextmanager
def inside_trigger_scope(ctx: Context):
    inside_trigger = ctx.inside_trigger
    ctx.inside_trigger = True

    yield

    ctx.inside_trigger = inside_trigger


@contextmanager
def inline_scope(ctx: Context):
    result_var = ctx.result_var
    ctx.result_var = None

    return_label = ctx.return_label
    ctx.return_label = None

    all_vars = ctx.all_vars.copy()
    old_inline = ctx._current_inline
    ctx._inline_counter += 1
    ctx._current_inline = ctx._inline_counter

    yield

    ctx.result_var = result_var
    ctx.return_label = return_label

    ctx.all_vars = all_vars
    ctx._current_inline = old_inline


@contextmanager
def self_scope(self_var, old_self_var, ctx: Context):
    all_vars = ctx.all_vars.copy()
    local_vars = ctx.locals.copy()
    ctx.all_vars[names.SELF] = self_var
    ctx.locals[names.SELF] = self_var
    ctx.all_vars[mangled.OLD_SELF] = old_self_var
    ctx.locals[mangled.OLD_SELF] = old_self_var

    yield

    ctx.all_vars = all_vars
    ctx.locals = local_vars


@contextmanager
def break_scope(ctx: Context):
    break_label = ctx.break_label
    ctx.break_label = ctx._next_break_label()

    yield

    ctx.break_label = break_label


@contextmanager
def continue_scope(ctx: Context):
    continue_label = ctx.continue_label
    ctx.continue_label = ctx._next_continue_label()

    yield

    ctx.continue_label = continue_label