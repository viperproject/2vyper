"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.ast import types
from twovyper.ast.ast_nodes import Node

from twovyper.translation import helpers
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context
from twovyper.translation.model import ModelTranslator
from twovyper.translation.type import TypeTranslator

from twovyper.verification import rules

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


class AllocationTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

        self.model_translator = ModelTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

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
