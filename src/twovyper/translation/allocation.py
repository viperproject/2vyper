"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.ast import names, types
from twovyper.ast.ast_nodes import Node

from twovyper.translation import helpers, mangled
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context
from twovyper.translation.model import ModelTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.verification import rules
from twovyper.verification.rules import Rules

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


class AllocationTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

        self.model_translator = ModelTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    @property
    def specification_translator(self):
        from twovyper.translation.specification import SpecificationTranslator
        return SpecificationTranslator(self.viper_ast)

    def get_allocated(self, allocated: Expr, address: Expr, ctx: Context, pos=None, info=None) -> Expr:
        key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
        value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
        return helpers.map_get(self.viper_ast, allocated, address, key_type, value_type, pos, info)

    def _check_allocation(self, node: Node, allocated: Expr, address: Expr, value: Expr, ctx: Context, pos=None, info=None) -> List[Stmt]:
        get_alloc = self.get_allocated(allocated, address, ctx, pos)
        cond = self.viper_ast.LeCmp(value, get_alloc, pos)
        stmts, modelt = self.model_translator.save_variables(ctx)
        apos = self.to_position(node, ctx, rules.REALLOCATE_FAIL, modelt=modelt)
        stmts.append(self.viper_ast.Assert(cond, apos, info))
        return stmts

    def _change_allocation(self, allocated: Expr, address: Expr, value: Expr, increase: bool, ctx: Context, pos=None, info=None) -> List[Stmt]:
        get_alloc = self.get_allocated(allocated, address, ctx, pos)
        func = self.viper_ast.Add if increase else self.viper_ast.Sub
        new_value = func(get_alloc, value, pos)
        key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
        value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
        set_alloc = helpers.map_set(self.viper_ast, allocated, address, new_value, key_type, value_type, pos)
        alloc_assign = self.viper_ast.LocalVarAssign(allocated, set_alloc, pos, info)
        return [alloc_assign]

    def allocate(self, allocated: Expr, address: Expr, amount: Expr, ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Adds `amount` wei to the allocation map entry of `address`.
        """
        return self._change_allocation(allocated, address, amount, True, ctx, pos, info)

    def reallocate(self, node: Node, allocated: Expr, frm: Expr, to: Expr, amount: Expr, ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Checks that `from` has sufficient allocation and then moves `amount` wei from `frm` to `to`.
        """
        check_allocation = self._check_allocation(node, allocated, frm, amount, ctx, pos, info)
        decs = self._change_allocation(allocated, frm, amount, False, ctx, pos)
        incs = self._change_allocation(allocated, to, amount, True, ctx, pos)
        return check_allocation + decs + incs

    def deallocate(self, node: Node, allocated: Expr, address: Expr, amount: Expr, ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Checks that `address` has sufficient allocation and then removes `amount` wei from the allocation map entry of `address`.
        """
        check_allocation = self._check_allocation(node, allocated, address, amount, ctx, pos, info)
        decs = self._change_allocation(allocated, address, amount, False, ctx, pos, info)
        return check_allocation + decs

    def _leak_check(self, node: Node, rule: Rules, ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Checks that the invariant knows about all ether allocated to the individual addresses, i.e., that
        given only the invariant and the state it is known for each address how much of the ether is
        allocated to them.
        """
        spec_translator = self.specification_translator

        allocated = ctx.current_state[mangled.ALLOCATED]
        new_allocated_name = ctx.new_local_var_name(mangled.ALLOCATED)
        fresh_allocated = TranslatedVar(mangled.ALLOCATED, new_allocated_name, allocated.type, self.viper_ast, pos)
        ctx.new_local_vars.append(fresh_allocated.var_decl(ctx))

        stmts = []
        with ctx.allocated_scope(fresh_allocated):
            for inv in ctx.program.invariants:
                ppos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                inv_stmts, expr = spec_translator.translate_invariant(inv, ctx, True)
                stmts.extend(inv_stmts)
                stmts.append(self.viper_ast.Inhale(expr, ppos))

        address = self.viper_ast.LocalVarDecl('$a', self.viper_ast.Int, pos)
        address_var = address.localVar()
        cond = self.viper_ast.LeCmp(self.viper_ast.IntLit(0, pos), address_var, pos)
        if not ctx.program.config.has_option(names.CONFIG_NO_OVERFLOWS):
            cmpm = self.viper_ast.LeCmp(address_var, self.viper_ast.IntLit(types.VYPER_ADDRESS.upper, pos), pos)
            cond = self.viper_ast.And(cond, cmpm, pos)
        allocated_get = self.get_allocated(allocated.local_var(ctx, pos), address_var, ctx, pos)
        fresh_allocated_get = self.get_allocated(fresh_allocated.local_var(ctx, pos), address_var, ctx, pos)
        allocated_eq = self.viper_ast.EqCmp(allocated_get, fresh_allocated_get, pos)
        trigger = self.viper_ast.Trigger([allocated_get, fresh_allocated_get], pos)
        assertion = self.viper_ast.Forall([address], [trigger], self.viper_ast.Implies(cond, allocated_eq, pos), pos)
        if ctx.function.name == names.INIT:
            # Leak check only has to hold if __init__ succeeds
            succ = ctx.success_var.local_var(ctx)
            assertion = self.viper_ast.Implies(succ, assertion, pos)

        model_stmts, modelt = self.model_translator.save_variables(ctx)
        stmts.extend(model_stmts)
        apos = self.to_position(node, ctx, rule, modelt=modelt)
        stmts.append(self.viper_ast.Assert(assertion, apos, info))

        return stmts

    def function_leak_check(self, ctx: Context, pos=None, info=None) -> List[Stmt]:
        return self._leak_check(ctx.function.node, rules.ALLOCATION_LEAK_CHECK_FAIL, ctx, pos, info)

    def send_leak_check(self, node: Node, ctx: Context, pos=None, info=None) -> List[Stmt]:
        return self._leak_check(node, rules.CALL_LEAK_CHECK_FAIL, ctx, pos, info)
