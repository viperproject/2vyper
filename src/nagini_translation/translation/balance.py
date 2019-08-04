"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from nagini_translation.ast import names

from nagini_translation.viper.ast import ViperAST
from nagini_translation.viper.typedefs import Expr, Stmt

from nagini_translation.translation.context import Context
from nagini_translation.translation.abstract import CommonTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation import helpers
from nagini_translation.translation import mangled


class BalanceTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

        self.type_translator = TypeTranslator(viper_ast)

    def get_balance(self, self_var: Expr, ctx: Context, pos=None, info=None) -> Expr:
        balance_type = ctx.field_types[names.SELF_BALANCE]
        return helpers.struct_get(self.viper_ast, self_var, names.SELF_BALANCE, balance_type, ctx.self_type, pos, info)

    def set_balance(self, self_var: Expr, value: Expr, ctx: Context, pos=None, info=None) -> Expr:
        return helpers.struct_set(self.viper_ast, self_var, value, names.SELF_BALANCE, ctx.self_type, pos, info)

    def check_balance(self, amount: Expr, ctx: Context, pos=None, info=None) -> Stmt:
        self_var = ctx.self_var.localVar()
        get_balance = self.get_balance(self_var, ctx, pos)
        return self.fail_if(self.viper_ast.LtCmp(get_balance, amount), [], ctx, pos, info)

    def increase_balance(self, amount: Expr, ctx: Context, pos=None, info=None) -> Stmt:
        self_var = ctx.self_var.localVar()
        get_balance = self.get_balance(self_var, ctx, pos)
        inc_sum = self.viper_ast.Add(get_balance, amount, pos)
        inc = self.set_balance(self_var, inc_sum, ctx, pos)
        return self.viper_ast.LocalVarAssign(self_var, inc, pos, info)

    def decrease_balance(self, amount: Expr, ctx: Context, pos=None, info=None) -> Stmt:
        self_var = ctx.self_var.localVar()
        get_balance = self.get_balance(self_var, ctx, pos)
        diff = self.viper_ast.Sub(get_balance, amount)
        sub = self.set_balance(self_var, diff, ctx, pos)
        return self.viper_ast.LocalVarAssign(self_var, sub, pos, info)

    def get_received(self, self_var: Expr, address: Expr, ctx: Context, pos=None, info=None):
        received_type = ctx.field_types[mangled.RECEIVED_FIELD]
        received = helpers.struct_get(self.viper_ast, self_var, mangled.RECEIVED_FIELD, received_type, ctx.self_type, pos)
        # TODO: improve this type stuff
        return helpers.map_get(self.viper_ast, received, address, self.viper_ast.Int, self.viper_ast.Int, pos)

    def get_sent(self, self_var: Expr, address: Expr, ctx: Context, pos=None, info=None):
        sent_type = ctx.field_types[mangled.SENT_FIELD]
        sent = helpers.struct_get(self.viper_ast, self_var, mangled.SENT_FIELD, sent_type, ctx.self_type, pos)
        # TODO: improve this type stuff
        return helpers.map_get(self.viper_ast, sent, address, self.viper_ast.Int, self.viper_ast.Int, pos)

    def increase_received(self, amount: Expr, ctx: Context, pos=None, info=None):
        self_var = ctx.self_var.localVar()
        # TODO: pass this as an argument
        msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
        rec_type = ctx.field_types[mangled.RECEIVED_FIELD]
        rec = helpers.struct_get(self.viper_ast, self_var, mangled.RECEIVED_FIELD, rec_type, ctx.self_type, pos)
        # TODO: improve this type stuff
        rec_sender = helpers.map_get(self.viper_ast, rec, msg_sender, self.viper_ast.Int, self.viper_ast.Int, pos)
        rec_inc_sum = self.viper_ast.Add(rec_sender, amount, pos)
        # TODO: improve this type stuff
        rec_set = helpers.map_set(self.viper_ast, rec, msg_sender, rec_inc_sum, self.viper_ast.Int, self.viper_ast.Int, pos)
        self_set = helpers.struct_set(self.viper_ast, self_var, rec_set, mangled.RECEIVED_FIELD, ctx.self_type, pos)
        return self.viper_ast.LocalVarAssign(self_var, self_set, pos, info)

    def increase_sent(self, to: Expr, amount: Expr, ctx: Context, pos=None, info=None):
        self_var = ctx.self_var.localVar()
        sent_type = ctx.field_types[mangled.SENT_FIELD]
        sent = helpers.struct_get(self.viper_ast, self_var, mangled.SENT_FIELD, sent_type, ctx.self_type, pos)
        # TODO: improve this type stuff
        sent_to = helpers.map_get(self.viper_ast, sent, to, self.viper_ast.Int, self.viper_ast.Int, pos)
        sent_inc = self.viper_ast.Add(sent_to, amount, pos)
        # TODO: improve this type stuff
        sent_set = helpers.map_set(self.viper_ast, sent, to, sent_inc, self.viper_ast.Int, self.viper_ast.Int, pos)
        self_set = helpers.struct_set(self.viper_ast, self_var, sent_set, mangled.SENT_FIELD, ctx.self_type, pos)
        return self.viper_ast.LocalVarAssign(self_var, self_set, pos, info)
