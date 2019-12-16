"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import contextmanager
from collections import ChainMap, defaultdict

from twovyper.ast import names
from twovyper.translation import mangled


class Context:

    def __init__(self):
        self.program = None
        # The program whose code is currently being translated, i.e., a VyperProgram
        # normally, and a VyperInterface when we translate interface specifications.
        self.current_program = None
        self.options = None
        # The translated types of all fields
        self.field_types = {}
        # Invariants that are known to be true and therefore don't need to be checked
        self.unchecked_invariants = []

        self.function = None

        self.args = {}
        self.locals = {}
        # The state which is currently regarded as 'present'
        self.current_state = {}
        # The state which is currently regarded as 'old'
        self.current_old_state = {}
        self.quantified_vars = {}

        # The actual present, old, pre, and issued states
        self.present_state = {}
        self.old_state = {}
        self.pre_state = {}
        self.issued_state = {}

        self.self_address = None

        self._break_label_counter = -1
        self._continue_label_counter = -1
        self.break_label = None
        self.continue_label = None

        self.success_var = None
        self.revert_label = None
        self.result_var = None
        self.return_label = None

        self.inside_trigger = False

        self._local_var_counter = defaultdict(lambda: -1)
        self.new_local_vars = []

        self._quantified_var_counter = -1
        self._inline_counter = -1
        self._current_inline = -1
        self.inline_vias = []

    @property
    def all_vars(self):
        return ChainMap(self.quantified_vars, self.current_state, self.locals, self.args)

    @property
    def self_type(self):
        return self.program.fields.type

    @property
    def self_var(self):
        """
        The variable declaration to which `self` currently refers.
        """
        return self.current_state[names.SELF]

    @property
    def old_self_var(self):
        """
        The variable declaration to which `old(self)` currently refers.
        """
        return self.current_old_state[names.SELF]

    @property
    def pre_self_var(self):
        """
        The state of `self` before the function call.
        """
        return self.pre_state[names.SELF]

    @property
    def issued_self_var(self):
        """
        The state of `self` when issuing the transaction.
        """
        return self.issued_state[names.SELF]

    @property
    def msg_var(self):
        return self.all_vars[names.MSG]

    @property
    def block_var(self):
        return self.all_vars[names.BLOCK]

    @property
    def tx_var(self):
        return self.all_vars[names.TX]

    def new_local_var_name(self, name: str) -> str:
        full_name = mangled.local_var_name(self.inline_prefix, name)
        self._local_var_counter[full_name] += 1
        new_count = self._local_var_counter[full_name]
        if new_count == 0:
            return full_name
        else:
            return f'{full_name}${new_count}'

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

    args = ctx.args
    locals = ctx.locals
    current_state = ctx.current_state
    current_old_state = ctx.current_old_state
    quantified_vars = ctx.quantified_vars

    present_state = ctx.present_state
    old_state = ctx.old_state
    pre_state = ctx.pre_state
    issued_state = ctx.issued_state

    self_address = ctx.self_address

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
    inline_vias = ctx.inline_vias.copy()

    ctx.function = None

    ctx.args = {}
    ctx.locals = {}
    ctx.current_state = {}
    ctx.current_old_state = {}
    ctx.quantified_vars = {}

    ctx.present_state = {}
    ctx.old_state = {}
    ctx.pre_state = {}
    ctx.issued_state = {}

    ctx._break_label_counter = -1
    ctx._continue_label_counter = -1
    ctx.break_label = None
    ctx.continue_label = None

    ctx.success_var = None
    ctx.revert_label = None
    ctx.result_var = None
    ctx.return_label = None

    ctx.inside_trigger = False

    ctx._local_var_counter = defaultdict(lambda: -1)
    ctx.new_local_vars = []

    ctx._quantified_var_counter = -1
    ctx._inline_counter = -1
    ctx._current_inline = -1

    yield

    ctx.function = function

    ctx.args = args
    ctx.locals = locals
    ctx.current_state = current_state
    ctx.current_old_state = current_old_state
    ctx.quantified_vars = quantified_vars

    ctx.present_state = present_state
    ctx.old_state = old_state
    ctx.pre_state = pre_state
    ctx.issued_state = issued_state

    ctx.self_address = self_address

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
    ctx.inline_vias = inline_vias


@contextmanager
def quantified_var_scope(ctx: Context):
    quantified_vars = ctx.quantified_vars.copy()
    quantified_var_counter = ctx._quantified_var_counter
    ctx._quantified_var_counter = -1

    yield

    ctx.quantified_vars = quantified_vars
    ctx._quantified_var_counter = quantified_var_counter


@contextmanager
def inside_trigger_scope(ctx: Context):
    inside_trigger = ctx.inside_trigger
    ctx.inside_trigger = True

    yield

    ctx.inside_trigger = inside_trigger


@contextmanager
def inline_scope(via, ctx: Context):
    result_var = ctx.result_var
    ctx.result_var = None

    return_label = ctx.return_label
    ctx.return_label = None

    local_vars = ctx.locals.copy()
    args = ctx.args.copy()
    old_inline = ctx._current_inline
    ctx._inline_counter += 1
    ctx._current_inline = ctx._inline_counter

    inline_vias = ctx.inline_vias.copy()
    ctx.inline_vias.append(via)

    yield

    ctx.result_var = result_var
    ctx.return_label = return_label

    ctx.locals = local_vars
    ctx.args = args
    ctx._current_inline = old_inline

    ctx.inline_vias = inline_vias


@contextmanager
def interface_call_scope(ctx: Context):
    result_var = ctx.result_var
    ctx.result_var = None
    success_var = ctx.success_var
    ctx.success_var = None

    local_vars = ctx.locals.copy()
    old_inline = ctx._current_inline
    ctx._inline_counter += 1
    ctx._current_inline = ctx._inline_counter

    yield

    ctx.result_var = result_var
    ctx.success_var = success_var

    ctx.locals = local_vars
    ctx._current_inline = old_inline


@contextmanager
def program_scope(program, ctx: Context):
    old_program = ctx.current_program
    ctx.current_program = program

    yield

    ctx.current_program = old_program


@contextmanager
def state_scope(present_state, old_state, ctx: Context):
    current_state = ctx.current_state.copy()
    current_old_state = ctx.current_old_state.copy()
    ctx.current_state = present_state
    ctx.current_old_state = old_state

    yield

    ctx.current_state = current_state
    ctx.current_old_state = current_old_state


@contextmanager
def self_address_scope(address, ctx: Context):
    old_self_address = ctx.self_address
    ctx.self_address = address

    yield

    ctx.self_address = old_self_address


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
