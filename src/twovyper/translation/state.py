"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.ast import names

from twovyper.translation import helpers, State
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Stmt


class StateTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

    def copy_state(self, from_state: State, to_state: State, ctx: Context, pos=None) -> List[Stmt]:
        copies = []
        for name in set(from_state) & set(to_state):
            to_var = to_state[name].local_var(ctx)
            from_var = from_state[name].local_var(ctx)
            copies.append(self.viper_ast.LocalVarAssign(to_var, from_var, pos))
        return self.seqn_with_info(copies, "Copy state")

    def havoc_state_except_self(self, state: State, ctx: Context, pos=None) -> List[Stmt]:
        """
        Havocs all contract state except self.
        """
        return self.havoc_state(state, ctx, pos, unless=lambda v: v == names.SELF)

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
        first_public_state = helpers.first_public_state_var(self.viper_ast, pos).localVar()
        old_assign = self.viper_ast.LocalVarAssign(old_self_var, self_var)
        false = self.viper_ast.FalseLit(pos)
        var_assign = self.viper_ast.LocalVarAssign(first_public_state, false, pos)
        stmts = [old_assign, var_assign] if set_false else [old_assign]
        return self.viper_ast.If(first_public_state, stmts, [], pos, info)
