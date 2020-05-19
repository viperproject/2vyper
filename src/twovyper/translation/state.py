"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Callable, List

from twovyper.ast import names

from twovyper.translation import helpers, mangled, State
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context
from twovyper.translation.variable import TranslatedVar
from twovyper.translation.type import TypeTranslator
from twovyper.verification import rules

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Stmt


class StateTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.type_translator = TypeTranslator(self.viper_ast)

    def state(self, name_transformation: Callable[[str], str], ctx: Context):
        def self_var(name):
            return TranslatedVar(names.SELF, name, ctx.self_type, self.viper_ast)

        def contract_var(name):
            contracts_type = helpers.contracts_type()
            return TranslatedVar(mangled.CONTRACTS, name, contracts_type, self.viper_ast)

        def allocated_var(name):
            allocated_type = helpers.allocated_type()
            return TranslatedVar(mangled.ALLOCATED, name, allocated_type, self.viper_ast)

        def offered_var(name):
            offered_type = helpers.offered_type()
            return TranslatedVar(mangled.OFFERED, name, offered_type, self.viper_ast)

        def trusted_var(name):
            trusted_type = helpers.trusted_type()
            return TranslatedVar(mangled.TRUSTED, name, trusted_type, self.viper_ast)

        s = {
            names.SELF: self_var(name_transformation(mangled.SELF)),
            mangled.CONTRACTS: contract_var(name_transformation(mangled.CONTRACTS))
        }

        if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
            s[mangled.ALLOCATED] = allocated_var(name_transformation(mangled.ALLOCATED))
            s[mangled.OFFERED] = offered_var(name_transformation(mangled.OFFERED))
            s[mangled.TRUSTED] = trusted_var(name_transformation(mangled.TRUSTED))

        return s

    @staticmethod
    def _is_local(state_var: str) -> bool:
        return state_var != mangled.CONTRACTS

    def initialize_state(self, state: State, res: List[Stmt], ctx: Context):
        """
        Initializes the state belonging to the current contract, namely self and allocated,
        to its default value.
        """
        for var in state.values():
            if self._is_local(var.name):
                default = self.type_translator.default_value(None, var.type, res, ctx)
                assign = self.viper_ast.LocalVarAssign(var.local_var(ctx), default)
                res.append(assign)

    def copy_state(self, from_state: State, to_state: State, res: List[Stmt], ctx: Context, pos=None):
        copies = []
        for name in set(from_state) & set(to_state):
            to_var = to_state[name].local_var(ctx)
            from_var = from_state[name].local_var(ctx)
            copies.append(self.viper_ast.LocalVarAssign(to_var, from_var, pos))

        self.seqn_with_info(copies, "Copy state", res)

    def assume_type_assumptions_for_state(self, state_dict: State, name: str, res, ctx):
        stmts = []
        for state_var in state_dict.values():
            type_assumptions = self.type_translator.type_assumptions(state_var.local_var(ctx),
                                                                     state_var.type, ctx)
            stmts.extend(self.viper_ast.Inhale(type_assumption) for type_assumption in type_assumptions)

        return self.seqn_with_info(stmts, f"{name} state assumptions", res)

    def havoc_state_except_self(self, state: State, res: List[Stmt], ctx: Context, pos=None):
        """
        Havocs all contract state except self and allocated.
        """
        return self.havoc_state(state, res, ctx, pos, unless=self._is_local)

    def havoc_state(self, state: State, res: List[Stmt], ctx: Context, pos=None, unless=None):
        havocs = []
        for var in state.values():
            if unless and unless(var.name):
                continue
            havoc_name = ctx.new_local_var_name('havoc')
            havoc_var = self.viper_ast.LocalVarDecl(havoc_name, var.var_decl(ctx).typ(), pos)
            ctx.new_local_vars.append(havoc_var)
            havocs.append(self.viper_ast.LocalVarAssign(var.local_var(ctx), havoc_var.localVar(), pos))

        self.seqn_with_info(havocs, "Havoc state", res)

    def havoc_old_and_current_state(self, specification_translator, res, ctx, pos=None):
        # Havoc states
        self.havoc_state(ctx.current_state, res, ctx, pos)
        self.havoc_state(ctx.current_old_state, res, ctx, pos)
        self.assume_type_assumptions_for_state(ctx.current_state, "Present", res, ctx)
        self.assume_type_assumptions_for_state(ctx.current_old_state, "Old", res, ctx)
        assume_invs = []
        # Assume Invariants for old state
        with ctx.state_scope(ctx.current_old_state, ctx.current_old_state):
            for inv in ctx.unchecked_invariants():
                assume_invs.append(self.viper_ast.Inhale(inv))

            for inv in ctx.program.invariants:
                cond = specification_translator.translate_invariant(inv, assume_invs, ctx, True)
                inv_pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                assume_invs.append(self.viper_ast.Inhale(cond, inv_pos))
        # Assume Invariants for current state
        with ctx.state_scope(ctx.current_state, ctx.current_state):
            for inv in ctx.unchecked_invariants():
                assume_invs.append(self.viper_ast.Inhale(inv))
        self.seqn_with_info(assume_invs, "Assume invariants", res)

    def check_first_public_state(self, res: List[Stmt], ctx: Context, set_false: bool, pos=None, info=None):
        stmts = []
        for name in ctx.current_state:
            if self._is_local(name):
                current_var = ctx.current_state[name].local_var(ctx)
                old_var = ctx.current_old_state[name].local_var(ctx)
                assign = self.viper_ast.LocalVarAssign(old_var, current_var)
                stmts.append(assign)

        first_public_state = helpers.first_public_state_var(self.viper_ast, pos).localVar()

        if set_false:
            false = self.viper_ast.FalseLit(pos)
            var_assign = self.viper_ast.LocalVarAssign(first_public_state, false, pos)
            stmts.append(var_assign)

        res.append(self.viper_ast.If(first_public_state, stmts, [], pos, info))
