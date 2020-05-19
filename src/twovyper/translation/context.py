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
        self.inside_inline_analysis = False

        self._local_var_counter = defaultdict(lambda: -1)
        self.new_local_vars = []

        self._quantified_var_counter = -1
        self._inline_counter = -1
        self._current_inline = -1
        self.inline_vias = []

    @property
    def all_vars(self) -> ChainMap:
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
    def chain_var(self):
        return self.all_vars[names.CHAIN]

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
    def function_scope(self):
        """
        Should be used in a ``with`` statement.
        Saves the current context state of a function, then clears it for the body
        of the ``with`` statement and restores the previous one in the end.
        """

        function = self.function

        args = self.args
        locals = self.locals
        current_state = self.current_state
        current_old_state = self.current_old_state
        quantified_vars = self.quantified_vars

        present_state = self.present_state
        old_state = self.old_state
        pre_state = self.pre_state
        issued_state = self.issued_state

        self_address = self.self_address

        _break_label_counter = self._break_label_counter
        _continue_label_counter = self._continue_label_counter
        break_label = self.break_label
        continue_label = self.continue_label

        success_var = self.success_var
        revert_label = self.revert_label
        result_var = self.result_var
        return_label = self.return_label

        inside_trigger = self.inside_trigger
        inside_inline_analysis = self.inside_inline_analysis

        local_var_counter = self._local_var_counter
        new_local_vars = self.new_local_vars

        quantified_var_counter = self._quantified_var_counter
        inline_counter = self._inline_counter
        current_inline = self._current_inline
        inline_vias = self.inline_vias.copy()

        self.function = None

        self.args = {}
        self.locals = {}
        self.current_state = {}
        self.current_old_state = {}
        self.quantified_vars = {}

        self.present_state = {}
        self.old_state = {}
        self.pre_state = {}
        self.issued_state = {}

        self._break_label_counter = -1
        self._continue_label_counter = -1
        self.break_label = None
        self.continue_label = None

        self.success_var = None
        self.revert_label = None
        self.result_var = None
        self.return_label = None

        self.inside_trigger = False
        self.inside_inline_analysis = False

        self._local_var_counter = defaultdict(lambda: -1)
        self.new_local_vars = []

        self._quantified_var_counter = -1
        self._inline_counter = -1
        self._current_inline = -1

        yield

        self.function = function

        self.args = args
        self.locals = locals
        self.current_state = current_state
        self.current_old_state = current_old_state
        self.quantified_vars = quantified_vars

        self.present_state = present_state
        self.old_state = old_state
        self.pre_state = pre_state
        self.issued_state = issued_state

        self.self_address = self_address

        self._break_label_counter = _break_label_counter
        self._continue_label_counter = _continue_label_counter
        self.break_label = break_label
        self.continue_label = continue_label

        self.success_var = success_var
        self.revert_label = revert_label
        self.result_var = result_var
        self.return_label = return_label

        self.inside_trigger = inside_trigger
        self.inside_inline_analysis = inside_inline_analysis

        self._local_var_counter = local_var_counter
        self.new_local_vars = new_local_vars

        self._quantified_var_counter = quantified_var_counter
        self._inline_counter = inline_counter
        self._current_inline = current_inline
        self.inline_vias = inline_vias

    @contextmanager
    def quantified_var_scope(self):
        quantified_vars = self.quantified_vars.copy()
        quantified_var_counter = self._quantified_var_counter
        self._quantified_var_counter = -1

        yield

        self.quantified_vars = quantified_vars
        self._quantified_var_counter = quantified_var_counter

    @contextmanager
    def inside_trigger_scope(self):
        inside_trigger = self.inside_trigger
        self.inside_trigger = True

        yield

        self.inside_trigger = inside_trigger

    @contextmanager
    def inline_scope(self, via):
        success_var = self.success_var
        result_var = self.result_var
        self.result_var = None

        return_label = self.return_label
        self.return_label = None

        local_vars = self.locals.copy()
        self.locals = {names.MSG: local_vars[names.MSG], names.BLOCK: local_vars[names.BLOCK],
                       names.CHAIN: local_vars[names.CHAIN], names.TX: local_vars[names.TX]}
        args = self.args.copy()
        old_inline = self._current_inline
        self._inline_counter += 1
        self._current_inline = self._inline_counter

        inline_vias = self.inline_vias.copy()
        self.inline_vias.append(via)

        inside_inline_analysis = self.inside_inline_analysis
        self.inside_inline_analysis = True

        yield

        self.success_var = success_var
        self.result_var = result_var
        self.return_label = return_label

        self.locals = local_vars
        self.args = args
        self._current_inline = old_inline

        self.inline_vias = inline_vias

        self.inside_inline_analysis = inside_inline_analysis

    @contextmanager
    def interface_call_scope(self):
        result_var = self.result_var
        self.result_var = None
        success_var = self.success_var
        self.success_var = None

        local_vars = self.locals.copy()
        old_inline = self._current_inline
        self._inline_counter += 1
        self._current_inline = self._inline_counter

        yield

        self.result_var = result_var
        self.success_var = success_var

        self.locals = local_vars
        self._current_inline = old_inline

    @contextmanager
    def program_scope(self, program):
        old_program = self.current_program
        self.current_program = program

        yield

        self.current_program = old_program

    @contextmanager
    def state_scope(self, present_state, old_state):
        current_state = self.current_state.copy()
        current_old_state = self.current_old_state.copy()
        self.current_state = present_state
        self.current_old_state = old_state

        yield

        self.current_state = current_state
        self.current_old_state = current_old_state

    @contextmanager
    def allocated_scope(self, allocated):
        current_state = self.current_state.copy()
        self.current_state[mangled.ALLOCATED] = allocated

        yield

        self.current_state = current_state

    @contextmanager
    def self_address_scope(self, address):
        old_self_address = self.self_address
        self.self_address = address

        yield

        self.self_address = old_self_address

    @contextmanager
    def break_scope(self):
        break_label = self.break_label
        self.break_label = self._next_break_label()

        yield

        self.break_label = break_label

    @contextmanager
    def continue_scope(self):
        continue_label = self.continue_label
        self.continue_label = self._next_continue_label()

        yield

        self.continue_label = continue_label
