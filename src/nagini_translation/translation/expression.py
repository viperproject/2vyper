"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.utils import flatten, first_index

from nagini_translation.ast import names
from nagini_translation.ast import types

from nagini_translation.ast.types import MapType, ArrayType

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.context import Context, use_old_scope

from nagini_translation.translation.builtins import (
    map_get, array_get, array_contains, array_not_contains
)

from nagini_translation.translation import builtins

from nagini_translation.exceptions import UnsupportedException

from nagini_translation.viper.ast import ViperAST
from nagini_translation.viper.typedefs import StmtsAndExpr
from nagini_translation.verification import rules


class ExpressionTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

        self._operations = {
            ast.USub: self.viper_ast.Minus,
            ast.Add: self.viper_ast.Add,
            ast.Sub: self.viper_ast.Sub,
            ast.Mult: self.viper_ast.Mul,
            ast.Div: self.viper_ast.Div,  # Note that / in Vyper means floor division
            ast.Mod: self.viper_ast.Mod,
            ast.Pow: lambda l, r, pos: builtins.pow(viper_ast, l, r, pos),
            ast.Eq: self.viper_ast.EqCmp,
            ast.NotEq: self.viper_ast.NeCmp,
            ast.Lt: self.viper_ast.LtCmp,
            ast.LtE: self.viper_ast.LeCmp,
            ast.Gt: self.viper_ast.GtCmp,
            ast.GtE: self.viper_ast.GeCmp,
            ast.In: lambda l, r, pos: array_contains(viper_ast, l, r, pos),
            ast.NotIn: lambda l, r, pos: array_not_contains(viper_ast, l, r, pos),
            ast.And: self.viper_ast.And,
            ast.Or: self.viper_ast.Or,
            ast.Not: self.viper_ast.Not
        }

    def translate_Num(self, node: ast.Num, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if isinstance(node.n, int):
            lit = self.viper_ast.IntLit(node.n, pos)
            return [], lit
        elif isinstance(node.n, float):
            raise UnsupportedException(node, "Float not yet supported")
        else:
            raise UnsupportedException(node, "Unsupported number literal")

    def translate_NameConstant(self, node: ast.NameConstant, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if node.value is True:
            return [], self.viper_ast.TrueLit(pos)
        elif node.value is False:
            return [], self.viper_ast.FalseLit(pos)
        else:
            raise UnsupportedException(node)

    def translate_Name(self, node: ast.Name, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)
        var_decl = ctx.all_vars[node.id]
        return [], self.viper_ast.LocalVar(var_decl.name(), var_decl.typ(), pos)

    def translate_BinOp(self, node: ast.BinOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        left_stmts, left = self.translate(node.left, ctx)
        right_stmts, right = self.translate(node.right, ctx)
        stmts = left_stmts + right_stmts

        op = self.translate_operator(node.op)

        # If the divisor is 0 revert the transaction
        if isinstance(node.op, ast.Div) or isinstance(node.op, ast.Mod):
            cond = self.viper_ast.EqCmp(right, self.viper_ast.IntLit(0, pos), pos)
            stmts.append(self.fail_if(cond, ctx, pos))

        # If the result of a uint subtraction is negative, revert the transaction
        if isinstance(node.op, ast.Sub) and types.is_unsigned(node.type):
            cond = self.viper_ast.GtCmp(right, left, pos)
            stmts.append(self.fail_if(cond, ctx, pos))

        return stmts, op(left, right, pos)

    def translate_BoolOp(self, node: ast.BoolOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        op = self.translate_operator(node.op)

        def build(values):
            head, *tail = values
            stmts, lhs = self.translate(head, ctx)
            if not tail:
                return stmts, lhs
            else:
                more, rhs = build(tail)
                return stmts + more, op(lhs, rhs, pos)

        return build(node.values)

    def translate_UnaryOp(self, node: ast.UnaryOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        op = self.translate_operator(node.op)

        stmts, expr = self.translate(node.operand, ctx)
        return stmts, op(expr, pos)

    def translate_Compare(self, node: ast.Compare, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        lhs_stmts, lhs = self.translate(node.left, ctx)
        op = self.translate_operator(node.ops[0])
        rhs_stmts, rhs = self.translate(node.comparators[0], ctx)

        return lhs_stmts + rhs_stmts, op(lhs, rhs, pos)

    def translate_operator(self, operator):
        return self._operations[type(operator)]

    def translate_Attribute(self, node: ast.Attribute, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        stmts, expr = self.translate(node.value, ctx)
        field = ctx.fields.get(node.attr, ctx.immutable_fields.get(node.attr))
        return stmts, self.viper_ast.FieldAccess(expr, field, pos)

    def translate_Subscript(self, node: ast.Subscript, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        value_stmts, value = self.translate(node.value, ctx)
        index_stmts, index = self.translate(node.slice.value, ctx)
        stmts = []

        node_type = node.value.type
        if isinstance(node_type, MapType):
            key_type = self.type_translator.translate(node_type.key_type, ctx)
            value_type = self.type_translator.translate(node_type.value_type, ctx)
            call = map_get(self.viper_ast, value, index, key_type, value_type, pos)
        elif isinstance(node_type, ArrayType):
            stmts.append(self.type_translator.array_bounds_check(value, index, ctx))
            element_type = self.type_translator.translate(node_type.element_type, ctx)
            call = array_get(self.viper_ast, value, index, element_type, pos)

        return value_stmts + index_stmts + stmts, call

    def translate_List(self, node: ast.List, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if not node.elts:
            type = self.type_translator.translate(node.type.element_type, ctx)
            return [], self.viper_ast.EmptySeq(type, pos)

        stmts = []
        elems = []
        for e in node.elts:
            e_stmts, elem = self.translate(e, ctx)
            stmts.extend(e_stmts)
            elems.append(elem)

        return stmts, self.viper_ast.ExplicitSeq(elems, pos)

    def translate_Str(self, node: ast.Str, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)
        if not node.s:
            type = self.type_translator.translate(node.type.element_type, ctx)
            return [], self.viper_ast.EmptySeq(type, pos)
        else:
            elems = [self.viper_ast.IntLit(e, pos) for e in bytes(node.s, 'utf-8')]
            return [], self.viper_ast.ExplicitSeq(elems, pos)

    def translate_Bytes(self, node: ast.Bytes, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)
        if not node.s:
            type = self.type_translator.translate(node.type.element_type, ctx)
            return [], self.viper_ast.EmptySeq(type, pos)
        else:
            elems = [self.viper_ast.IntLit(e, pos) for e in node.s]
            return [], self.viper_ast.ExplicitSeq(elems, pos)

    def translate_Call(self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if isinstance(node.func, ast.Name):
            name = node.func.id
            is_min = (name == names.MIN)
            is_max = (name == names.MAX)
            if is_min or is_max:
                lhs_stmts, lhs = self.translate(node.args[0], ctx)
                rhs_stmts, rhs = self.translate(node.args[1], ctx)
                op = self.viper_ast.GtCmp if is_max else self.viper_ast.LtCmp
                comp = op(lhs, rhs, pos)
                stmts = lhs_stmts + rhs_stmts
                return stmts, self.viper_ast.CondExp(comp, lhs, rhs, pos)
            elif name == names.AS_WEI_VALUE:
                arg_stmts, arg = self.translate(node.args[0], ctx)
                unit = node.args[1].s
                unit_pos = self.to_position(node.args[1], ctx)
                multiplier = self.viper_ast.IntLit(names.ETHER_UNITS[unit], unit_pos)
                return arg_stmts, self.viper_ast.Mul(arg, multiplier, pos)
            elif name == names.AS_UNITLESS_NUMBER:
                return self.translate(node.args[0], ctx)
            elif name == names.LEN:
                arr_stmts, arr = self.translate(node.args[0], ctx)
                return arr_stmts, self.viper_ast.SeqLength(arr, pos)
            elif name == names.CONCAT:
                concat_stmts, concats = zip(*[self.translate(arg, ctx) for arg in node.args])

                def concat(args):
                    arg, *tail = args
                    if not tail:
                        return arg
                    else:
                        return self.viper_ast.SeqAppend(arg, concat(tail), pos)

                return flatten(concat_stmts), concat(concats)
            elif name == names.KECCAK256:
                arg_stmts, arg = self.translate(node.args[0], ctx)
                return arg_stmts, builtins.array_keccak256(self.viper_ast, arg, pos)
            elif name == names.SHA256:
                arg_stmts, arg = self.translate(node.args[0], ctx)
                return arg_stmts, builtins.array_sha256(self.viper_ast, arg, pos)
            elif name == names.SEND or name == names.RAW_CALL:
                # Sends are translated as follows:
                #    - Evaluate arguments to and amount
                #    - Check that balance is sufficient (self.balance >= amount) else revert
                #    - Subtract amount from self.balance (self.balance -= amount)
                #    - Check invariants
                #    - Exhale field permissions (forget all values)
                #    - Inhale field permissions
                #    - Assume invariants (where old refers to the state before send)
                #    - Assume unchecked invariants

                to_stmts, to = self.translate(node.args[0], ctx)

                if name == names.SEND:
                    amount_stmts, amount = self.translate(node.args[1], ctx)
                else:
                    # Translate the function expression (bytes)
                    function_stmts, _ = self.translate(node.args[1], ctx)
                    to_stmts.extend(function_stmts)
                    # Get the index of the value expression
                    val_idx = first_index(lambda n: n.arg == names.RAW_CALL_VALUE, node.keywords)
                    if val_idx >= 0:
                        amount_stmts, amount = self.translate(node.keywords[val_idx].value, ctx)
                    else:
                        amount_stmts, amount = [], self.viper_ast.IntLit(0, pos)

                self_balance = self.viper_ast.FieldAccess(ctx.self_var.localVar(), ctx.balance_field)
                lt = self.viper_ast.LtCmp(self_balance, amount)
                eq = self.viper_ast.EqCmp(self.viper_ast.IntLit(0), amount)
                check = self.fail_if(self.viper_ast.Or(lt, eq), ctx)

                sub = self.viper_ast.Sub(self_balance, amount)
                sub_stmt = self.viper_ast.FieldAssign(self_balance, sub)

                sent_get = builtins.self_sent_map_get(self.viper_ast, to, pos)
                sent_add = self.viper_ast.Add(sent_get, amount, pos)
                sent_acc = builtins.self_sent_field_acc(self.viper_ast, pos)
                sent_set = builtins.self_sent_map_set(self.viper_ast, to, sent_add, pos)
                sent_assign = self.viper_ast.FieldAssign(sent_acc, sent_set, pos)

                stmts = [*to_stmts, *amount_stmts, check, sub_stmt, sent_assign]

                with use_old_scope(False, ctx):
                    invs = ctx.invariants(ctx)
                inv_assertions = []
                for inv in invs:
                    via = [('invariant', inv.pos())]
                    call_pos = self.to_position(node, ctx, rules.CALL_INVARIANT_FAIL, via)
                    inv_assertions.append(self.viper_ast.Assert(inv, call_pos))
                ex_fields = [self.viper_ast.Exhale(perm) for perm in ctx.permissions]
                in_fields = [self.viper_ast.Inhale(perm) for perm in ctx.permissions]
                inh_exh = ex_fields + in_fields

                uinvs = ctx.unchecked_invariants
                assume_invs = []
                for inv, expr in zip(ctx.program.invariants, invs):
                    ipos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                    assume_invs.append(self.viper_ast.Inhale(expr, ipos))
                assume_unchecked = [self.viper_ast.Inhale(inv) for inv in uinvs]
                assumes = assume_invs + assume_unchecked

                send_fail_name = ctx.new_local_var_name('send_fail')
                send_fail = self.viper_ast.LocalVarDecl(send_fail_name, self.viper_ast.Bool)
                ctx.new_local_vars.append(send_fail)
                fail = self.fail_if(send_fail.localVar(), ctx)

                afters = [fail] + ctx.copy_old

                if name == names.RAW_CALL:
                    ret_name = ctx.new_local_var_name('raw_ret')
                    ret_type = self.type_translator.translate(node.type, ctx)
                    ret_var = self.viper_ast.LocalVarDecl(ret_name, ret_type, pos)
                    ctx.new_local_vars.append(ret_var)
                    return_value = ret_var.localVar()
                else:
                    return_value = None

                return stmts + inv_assertions + ctx.copy_old + inh_exh + assumes + afters, return_value
        else:
            name = node.func.attr
            stmts = []
            args = []
            for arg in node.args:
                arg_stmts, arg_expr = self.translate(arg, ctx)
                stmts.extend(arg_stmts)
                args.append(arg_expr)

            if node.func.value.id == names.LOG:
                return self._seqn_with_info(stmts, f"Event: {name}"), None
            else:
                call_stmts, res = ctx.inlined[name](args, ctx)
                return stmts + call_stmts, res
