"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.ast import types

from twovyper.translation import helpers
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context
from twovyper.translation.type import TypeTranslator

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


class AllocationTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

        self.type_translator = TypeTranslator(viper_ast)

    def get_allocated(self, allocated: Expr, address: Expr, ctx: Context, pos=None, info=None) -> Expr:
        key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
        value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
        return helpers.map_get(self.viper_ast, allocated, address, key_type, value_type, pos, info)

    def _change_allocation(self, allocated: Expr, address: Expr, value: Expr, increase: bool, ctx: Context, pos=None, info=None) -> List[Stmt]:
        get_alloc = self.get_allocated(allocated, address, ctx, pos)
        func = self.viper_ast.Add if increase else self.viper_ast.Sub
        new_value = func(get_alloc, value, pos)
        key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
        value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
        set_alloc = helpers.map_set(self.viper_ast, allocated, address, new_value, key_type, value_type, pos)
        alloc_assign = self.viper_ast.LocalVarAssign(allocated, set_alloc, pos, info)
        return [alloc_assign]

    def allocate(self, allocated: Expr, address: Expr, value: Expr, ctx: Context, pos=None, info=None) -> List[Stmt]:
        return self._change_allocation(allocated, address, value, True, ctx, pos, info)

    def reallocate(self, allocated: Expr, frm: Expr, to: Expr, amount: Expr, ctx: Context, pos=None, info=None) -> List[Stmt]:
        decs = self._change_allocation(allocated, frm, amount, False, ctx, pos, info)
        incs = self._change_allocation(allocated, to, amount, True, ctx, pos)
        return decs + incs

    def deallocate(self, allocated: Expr, address: Expr, value: Expr, ctx: Context, pos=None, info=None) -> List[Stmt]:
        return self._change_allocation(allocated, address, value, False, ctx, pos, info)
