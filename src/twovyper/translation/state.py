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

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Stmt


class StateTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

    def state(self, name_transformation: Callable[[str], str], ctx: Context):
        def self_var(name):
            return TranslatedVar(names.SELF, name, ctx.self_type, self.viper_ast)

        def contract_var(name):
            contracts_type = helpers.contracts_type()
            return TranslatedVar(mangled.CONTRACTS, name, contracts_type, self.viper_ast)

        def allocated_var(name):
            allocated_type = helpers.allocated_type()
            return TranslatedVar(mangled.ALLOCATED, name, allocated_type, self.viper_ast)

        s = {
            names.SELF: self_var(name_transformation(mangled.SELF)),
            mangled.CONTRACTS: contract_var(name_transformation(mangled.CONTRACTS))
        }

        if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
            s[mangled.ALLOCATED] = allocated_var(name_transformation(mangled.ALLOCATED))

        return s

    def copy_state(self, from_state: State, to_state: State, ctx: Context, pos=None) -> List[Stmt]:
        copies = []
        for name in set(from_state) & set(to_state):
            to_var = to_state[name].local_var(ctx)
            from_var = from_state[name].local_var(ctx)
            copies.append(self.viper_ast.LocalVarAssign(to_var, from_var, pos))
        return self.seqn_with_info(copies, "Copy state")

    def havoc_state_except_self(self, state: State, ctx: Context, pos=None) -> List[Stmt]:
        """
        Havocs all contract state except self and allocated.
        """
        return self.havoc_state(state, ctx, pos, unless=lambda v: v in [names.SELF, mangled.ALLOCATED])

    def havoc_state(self, state: State, ctx: Context, pos=None, unless=None) -> List[Stmt]:
        havocs = []
        for var in ctx.current_state.values():
            if unless and unless(var.name):
                continue
            havoc_name = ctx.new_local_var_name('havoc')
            havoc_var = self.viper_ast.LocalVarDecl(havoc_name, var.var_decl(ctx).typ(), pos)
            ctx.new_local_vars.append(havoc_var)
            havocs.append(self.viper_ast.LocalVarAssign(var.local_var(ctx), havoc_var.localVar(), pos))
        return self.seqn_with_info(havocs, "Havoc state")

    def check_first_public_state(self, ctx: Context, set_false: bool, pos=None, info=None) -> Stmt:
        self_var = ctx.self_var.local_var(ctx)
        old_self_var = ctx.old_self_var.local_var(ctx)
        self_assign = self.viper_ast.LocalVarAssign(old_self_var, self_var)

        stmts = [self_assign]

        if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
            allocated_var = ctx.current_state[mangled.ALLOCATED].local_var(ctx)
            old_allocated_var = ctx.current_old_state[mangled.ALLOCATED].local_var(ctx)
            allocated_assign = self.viper_ast.LocalVarAssign(old_allocated_var, allocated_var)
            stmts.append(allocated_assign)

        first_public_state = helpers.first_public_state_var(self.viper_ast, pos).localVar()

        if set_false:
            false = self.viper_ast.FalseLit(pos)
            var_assign = self.viper_ast.LocalVarAssign(first_public_state, false, pos)
            stmts.append(var_assign)

        return self.viper_ast.If(first_public_state, stmts, [], pos, info)
