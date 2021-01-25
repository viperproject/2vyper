"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import contextmanager
from collections import ChainMap, defaultdict
from typing import Dict, TYPE_CHECKING, List, Any, Optional, Tuple, Callable

from twovyper.ast import names
from twovyper.ast.ast_nodes import Expr, Node
from twovyper.ast.nodes import VyperFunction, VyperProgram
from twovyper.translation import mangled

if TYPE_CHECKING:
    from twovyper.translation.variable import TranslatedVar
    from twovyper.translation import LocalVarSnapshot


class Context:

    def __init__(self):
        self.program: Optional[VyperProgram] = None
        # The program whose code is currently being translated, i.e., a VyperProgram
        # normally, and a VyperInterface when we translate interface specifications.
        self.current_program: Optional[VyperProgram] = None
        self.options = None
        # The translated types of all fields
        self.field_types = {}
        # Invariants that are known to be true and therefore don't need to be checked
        self.unchecked_invariants: Optional[Callable[[], List[Expr]]] = None
        # Transitive postconditions that are known to be true and therefore don't need to be checked
        self.unchecked_transitive_postconditions: Optional[Callable[[], List[Expr]]] = None
        # Invariants for derived resources
        self.derived_resources_invariants: Optional[Callable[[Optional[Node]], List[Expr]]] = None

        self.function: Optional[VyperFunction] = None
        self.is_pure_function = False
        self.inline_function: Optional[VyperFunction] = None

        self.args = {}
        self.locals: Dict[str, TranslatedVar] = {}
        self.old_locals: Dict[str, TranslatedVar] = {}
        # The state which is currently regarded as 'present'
        self.current_state = {}
        # The state which is currently regarded as 'old'
        self.current_old_state = {}
        self.quantified_vars: Dict[str, TranslatedVar] = {}

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

        self.success_var: Optional[TranslatedVar] = None
        self.revert_label = None
        self.result_var: Optional[TranslatedVar] = None
        self.return_label = None

        self.inside_trigger = False
        self.inside_inline_analysis = False
        self.inline_function = None

        self.inside_lemma = False
        self.inside_interpreted = False

        self._local_var_counter = defaultdict(lambda: -1)
        self.new_local_vars = []

        self.loop_arrays: Dict[str, Expr] = {}
        self.loop_indices: Dict[str, TranslatedVar] = {}

        self.event_vars: Dict[str, List[Any]] = {}

        # And-ed conditions which must be all true when an assignment is made in a pure translator.
        self.pure_conds: Optional[Expr] = None
        # List of all assignments to the result variable
        # The tuple consists of an expression which is the condition under which the assignment happened and
        # the index of the variable (since this is SSA like, the result_var has many indices)
        self.pure_returns: List[Tuple[Expr, int]] = []
        # List of all assignments to the success variable
        # The tuple consists of an expression which is the condition under which the assignment happened and
        # the index of the variable (since this is SSA like, the success_var has many indices)
        self.pure_success: List[Tuple[Expr, int]] = []
        # List of all break statements in a loop
        # The tuple consists of an expression which is the condition under which the break statement is reached and
        # the dict is a snapshot of the local variables at the moment of the break statement
        self.pure_continues: List[Tuple[Optional[Expr], LocalVarSnapshot]] = []
        # List of all continue statements in a loop
        # The tuple consists of an expression which is the condition under which the continue statement is reached and
        # the dict is a snapshot of the local variables at the moment of the continue statement
        self.pure_breaks: List[Tuple[Optional[Expr], LocalVarSnapshot]] = []

        self._pure_var_index_counter = 1  # It has to start at 2
        self._quantified_var_counter = -1
        self._inline_counter = -1
        self._current_inline = -1
        self.inline_vias = []

        self.inside_interface_call = False
        self.inside_derived_resource_performs = False
        self.inside_performs_only_interface_call = False

    @property
    def current_function(self) -> Optional[VyperFunction]:
        return self.function if not self.inside_inline_analysis else self.inline_function

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

    def next_pure_var_index(self) -> int:
        self._pure_var_index_counter += 1
        return self._pure_var_index_counter

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
        is_pure_function = self.is_pure_function

        args = self.args
        local_variables = self.locals
        old_locals = self.old_locals
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
        inline_function = self.inline_function

        local_var_counter = self._local_var_counter
        new_local_vars = self.new_local_vars

        quantified_var_counter = self._quantified_var_counter
        inline_counter = self._inline_counter
        current_inline = self._current_inline
        inline_vias = self.inline_vias.copy()

        loop_arrays = self.loop_arrays
        loop_indices = self.loop_indices

        event_vars = self.event_vars

        pure_conds = self.pure_conds
        pure_returns = self.pure_returns
        pure_success = self.pure_success
        pure_var_index_counter = self._pure_var_index_counter
        pure_continues = self.pure_continues
        pure_breaks = self.pure_breaks

        inside_interface_call = self.inside_interface_call
        inside_derived_resource_performs = self.inside_derived_resource_performs

        self.function = None
        self.is_pure_function = False

        self.args = {}
        self.locals = {}
        self.old_locals = {}
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
        self.inline_function = None

        self._local_var_counter = defaultdict(lambda: -1)
        self.new_local_vars = []

        self._quantified_var_counter = -1
        self._inline_counter = -1
        self._current_inline = -1

        self.loop_arrays = {}
        self.loop_indices = {}

        self.event_vars = {}

        self.pure_conds = None
        self.pure_returns = []
        self.pure_success = []
        self._pure_var_index_counter = 1
        self.pure_continues = []
        self.pure_breaks = []

        self.inside_interface_call = False
        self.inside_derived_resource_performs = False

        yield

        self.function = function
        self.is_pure_function = is_pure_function

        self.args = args
        self.locals = local_variables
        self.old_locals = old_locals
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
        self.inline_function = inline_function

        self._local_var_counter = local_var_counter
        self.new_local_vars = new_local_vars

        self._quantified_var_counter = quantified_var_counter
        self._inline_counter = inline_counter
        self._current_inline = current_inline
        self.inline_vias = inline_vias

        self.loop_arrays = loop_arrays
        self.loop_indices = loop_indices

        self.event_vars = event_vars

        self.pure_conds = pure_conds
        self.pure_returns = pure_returns
        self.pure_success = pure_success
        self._pure_var_index_counter = pure_var_index_counter
        self.pure_continues = pure_continues
        self.pure_breaks = pure_breaks

        self.inside_interface_call = inside_interface_call
        self.inside_derived_resource_performs = inside_derived_resource_performs

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
    def inline_scope(self, via, function: Optional[VyperFunction] = None):
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
        inline_function = self.inline_function
        self.inline_function = function

        yield

        self.success_var = success_var
        self.result_var = result_var
        self.return_label = return_label

        self.locals = local_vars
        self.args = args
        self._current_inline = old_inline

        self.inline_vias = inline_vias

        self.inside_inline_analysis = inside_inline_analysis
        self.inline_function = inline_function

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

        inside_interface_call = self.inside_interface_call
        self.inside_interface_call = True

        yield

        self.result_var = result_var
        self.success_var = success_var

        self.locals = local_vars
        self._current_inline = old_inline

        self.inside_interface_call = inside_interface_call

    @contextmanager
    def derived_resource_performs_scope(self):
        inside_derived_resource_performs = self.inside_derived_resource_performs
        self.inside_derived_resource_performs = True

        inside_interface_call = self.inside_interface_call
        self.inside_interface_call = False

        yield

        self.inside_derived_resource_performs = inside_derived_resource_performs

        self.inside_interface_call = inside_interface_call

    @contextmanager
    def program_scope(self, program: VyperProgram):
        old_program: VyperProgram = self.current_program
        self.current_program = program

        args = None
        if self.function and not self.inside_inline_analysis:
            interfaces = [name for name, interface in old_program.interfaces.items() if interface.file == program.file]
            implemented_interfaces = [interface.name for interface in old_program.implements]
            if any(interface in implemented_interfaces for interface in interfaces):
                args = self.args
                other_func: VyperFunction = program.functions.get(self.function.name)
                if other_func:
                    assert len(other_func.args) == len(args)
                    self.args = {}
                    for (name, _), (_, var) in zip(other_func.args.items(), args.items()):
                        self.args[name] = var
        yield

        self.current_program = old_program
        if args:
            self.args = args

    @contextmanager
    def state_scope(self, present_state, old_state):
        current_state = self.current_state.copy()
        current_old_state = self.current_old_state.copy()
        self.current_state = present_state
        self.current_old_state = old_state

        local_vars = self.locals.copy()

        yield

        self.current_state = current_state
        self.current_old_state = current_old_state

        self.locals = local_vars

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

        pure_break = self.pure_breaks
        self.pure_breaks = []

        yield

        self.break_label = break_label

        self.pure_breaks = pure_break

    @contextmanager
    def continue_scope(self):
        continue_label = self.continue_label
        self.continue_label = self._next_continue_label()

        pure_continue = self.pure_continues
        self.pure_continues = []

        yield

        self.continue_label = continue_label

        self.pure_continues = pure_continue

    @contextmanager
    def old_local_variables_scope(self, old_locals):
        prev_old_locals = self.old_locals
        self.old_locals = old_locals

        yield

        self.old_locals = prev_old_locals

    @contextmanager
    def new_local_scope(self):
        event_vars = self.event_vars

        yield

        self.event_vars = event_vars

    @contextmanager
    def lemma_scope(self, is_inside=True):
        inside_lemma = self.inside_lemma
        self.inside_lemma = is_inside

        yield

        self.inside_lemma = inside_lemma

    @contextmanager
    def interpreted_scope(self, is_inside=True):
        inside_interpreted = self.inside_interpreted
        self.inside_interpreted = is_inside

        yield

        self.inside_interpreted = inside_interpreted
