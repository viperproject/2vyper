"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from itertools import chain
from contextlib import contextmanager

from nagini_translation.ast import names


class Context:

    def __init__(self, file: str):
        self.file = file
        self.program = None
        # All Vyper self-fields not including ghost fields
        self.fields = {}
        # Permissions of fields that have to be passed around
        # Note: already translated, as they should never fail
        self.permissions = []
        # Non-self fields like msg.sender which are immutable
        self.immutable_fields = {}
        # Permissions of immutable that have to be passed around
        # Note: already translated, as they should never fail
        self.immutable_permissions = []
        # Invariants that are not checked at the end of each function but just assumed, namely
        # conditions like non-negativeness for uint256
        # Note: already translated, as they are never checked and therfore cannot fail
        # Global: About globally available fields, i.e. self fields
        self.global_unchecked_invariants = []
        # Local: About locally available fields, i.e. msg and block fields
        self.local_unchecked_invariants = []

        self.function = None

        self.all_vars = {}
        self.args = {}
        self.locals = {}
        self.quantified_vars = {}

        # The expressions to save the current state as 'old' state
        self.copy_old = []
        # True if being inside an old statement
        self.inside_old = False
        # The old label to use if Viper 'old' statements are used
        self.old_label = None

        self._break_label_counter = -1
        self._continue_label_counter = -1
        self.break_label = None
        self.continue_label = None

        self.success_var = None
        self.revert_label = None
        self.result_var = None
        self.end_label = None

        self._local_var_counter = -1
        self.new_local_vars = []

        self._quantified_var_counter = -1
        self._inline_counter = -1
        self._current_inline = -1

    @property
    def self_var(self):
        return self.all_vars[names.SELF]

    @property
    def msg_var(self):
        return self.all_vars[names.MSG]

    @property
    def block_var(self):
        return self.all_vars[names.BLOCK]

    @property
    def balance_field(self):
        return self.fields[names.SELF_BALANCE]

    @property
    def unchecked_invariants(self):
        return chain(self.global_unchecked_invariants, self.local_unchecked_invariants)

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

    copy_old = ctx.copy_old
    inside_old = ctx.inside_old
    old_label = ctx.old_label

    _break_label_counter = ctx._break_label_counter
    _continue_label_counter = ctx._continue_label_counter
    break_label = ctx.break_label
    continue_label = ctx.continue_label

    success_var = ctx.success_var
    revert_label = ctx.revert_label
    result_var = ctx.result_var
    end_label = ctx.end_label

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

    ctx.copy_old = []
    ctx.inside_old = False
    ctx.old_label = None

    ctx._break_label_counter = -1
    ctx._continue_label_counter = -1
    ctx.break_label = None
    ctx.continue_label = None

    ctx.success_var = None
    ctx.revert_label = None
    ctx.result_var = None
    ctx.end_label = None

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

    ctx.copy_old = copy_old
    ctx.inside_old = inside_old
    ctx.old_label = old_label

    ctx._break_label_counter = _break_label_counter
    ctx._continue_label_counter = _continue_label_counter
    ctx.break_label = break_label
    ctx.continue_label = continue_label

    ctx.success_var = success_var
    ctx.revert_label = revert_label
    ctx.result_var = result_var
    ctx.end_label = end_label

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
def inline_scope(ctx: Context):
    result_var = ctx.result_var
    ctx.result_var = None

    end_label = ctx.end_label
    ctx.end_label = None

    all_vars = ctx.all_vars.copy()
    old_inline = ctx._current_inline
    ctx._inline_counter += 1
    ctx._current_inline = ctx._inline_counter

    yield

    ctx.result_var = result_var
    ctx.end_label = end_label

    ctx.all_vars = all_vars
    ctx._current_inline = old_inline


@contextmanager
def inside_old_scope(ctx: Context):
    inside_old = ctx.inside_old
    ctx.inside_old = True

    yield

    ctx.inside_old = inside_old


@contextmanager
def old_label_scope(label, ctx: Context):
    old_label = ctx.old_label
    ctx.old_label = label

    yield

    ctx.old_label = old_label


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
