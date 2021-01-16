"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.ast import names

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt

from twovyper.translation.context import Context
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation import helpers
from twovyper.translation import mangled


class BalanceTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

        self.type_translator = TypeTranslator(viper_ast)

    def get_balance(self, self_var: Expr, ctx: Context, pos=None, info=None) -> Expr:
        balance_type = ctx.field_types[names.ADDRESS_BALANCE]
        return helpers.struct_get(self.viper_ast, self_var, names.ADDRESS_BALANCE, balance_type, ctx.self_type, pos, info)

    def set_balance(self, self_var: Expr, value: Expr, ctx: Context, pos=None, info=None) -> Expr:
        balance_type = ctx.field_types[names.ADDRESS_BALANCE]
        return helpers.struct_set(self.viper_ast, self_var, value, names.ADDRESS_BALANCE, balance_type, ctx.self_type, pos, info)

    def check_balance(self, amount: Expr, res: List[Stmt], ctx: Context, pos=None, info=None):
        self_var = ctx.self_var.local_var(ctx)
        get_balance = self.get_balance(self_var, ctx, pos)
        self.fail_if(self.viper_ast.LtCmp(get_balance, amount), [], res, ctx, pos, info)

    def increase_balance(self, amount: Expr, res: List[Stmt], ctx: Context, pos=None, info=None):
        self_var = ctx.self_var.local_var(ctx)
        get_balance = self.get_balance(self_var, ctx, pos)
        inc_sum = self.viper_ast.Add(get_balance, amount, pos)
        inc = self.set_balance(self_var, inc_sum, ctx, pos)
        res.append(self.viper_ast.LocalVarAssign(self_var, inc, pos, info))

    def decrease_balance(self, amount: Expr, res: List[Stmt], ctx: Context, pos=None, info=None):
        self_var = ctx.self_var.local_var(ctx)
        get_balance = self.get_balance(self_var, ctx, pos)
        diff = self.viper_ast.Sub(get_balance, amount)
        sub = self.set_balance(self_var, diff, ctx, pos)
        res.append(self.viper_ast.LocalVarAssign(self_var, sub, pos, info))

    def received(self, self_var: Expr, ctx: Context, pos=None, info=None) -> Expr:
        received_type = ctx.field_types[mangled.RECEIVED_FIELD]
        return helpers.struct_get(self.viper_ast, self_var, mangled.RECEIVED_FIELD, received_type, ctx.self_type, pos, info)

    def sent(self, self_var: Expr, ctx: Context, pos=None, info=None) -> Expr:
        sent_type = ctx.field_types[mangled.SENT_FIELD]
        return helpers.struct_get(self.viper_ast, self_var, mangled.SENT_FIELD, sent_type, ctx.self_type, pos, info)

    def get_received(self, self_var: Expr, address: Expr, ctx: Context, pos=None, info=None) -> Expr:
        received = self.received(self_var, ctx, pos)
        return helpers.map_get(self.viper_ast, received, address, self.viper_ast.Int, self.viper_ast.Int, pos)

    def get_sent(self, self_var: Expr, address: Expr, ctx: Context, pos=None, info=None) -> Expr:
        sent = self.sent(self_var, ctx, pos)
        return helpers.map_get(self.viper_ast, sent, address, self.viper_ast.Int, self.viper_ast.Int, pos)

    def increase_received(self, amount: Expr, res: List[Stmt], ctx: Context, pos=None, info=None):
        self_var = ctx.self_var.local_var(ctx)
        # TODO: pass this as an argument
        msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
        rec_type = ctx.field_types[mangled.RECEIVED_FIELD]
        rec = helpers.struct_get(self.viper_ast, self_var, mangled.RECEIVED_FIELD, rec_type, ctx.self_type, pos)
        rec_sender = helpers.map_get(self.viper_ast, rec, msg_sender, self.viper_ast.Int, self.viper_ast.Int, pos)
        rec_inc_sum = self.viper_ast.Add(rec_sender, amount, pos)
        rec_set = helpers.map_set(self.viper_ast, rec, msg_sender, rec_inc_sum, self.viper_ast.Int, self.viper_ast.Int, pos)
        self_set = helpers.struct_set(self.viper_ast, self_var, rec_set, mangled.RECEIVED_FIELD, rec_type, ctx.self_type, pos)
        res.append(self.viper_ast.LocalVarAssign(self_var, self_set, pos, info))

    def increase_sent(self, to: Expr, amount: Expr, res: List[Stmt], ctx: Context, pos=None, info=None):
        self_var = ctx.self_var.local_var(ctx)
        sent_type = ctx.field_types[mangled.SENT_FIELD]
        sent = helpers.struct_get(self.viper_ast, self_var, mangled.SENT_FIELD, sent_type, ctx.self_type, pos)
        sent_to = helpers.map_get(self.viper_ast, sent, to, self.viper_ast.Int, self.viper_ast.Int, pos)
        sent_inc = self.viper_ast.Add(sent_to, amount, pos)
        sent_set = helpers.map_set(self.viper_ast, sent, to, sent_inc, self.viper_ast.Int, self.viper_ast.Int, pos)
        self_set = helpers.struct_set(self.viper_ast, self_var, sent_set, mangled.SENT_FIELD, sent_type, ctx.self_type, pos)
        res.append(self.viper_ast.LocalVarAssign(self_var, self_set, pos, info))
