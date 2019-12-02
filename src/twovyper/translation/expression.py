"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from itertools import chain
from typing import List, Optional, Tuple

from twovyper.utils import switch, flatten, first_index
from twovyper.exceptions import UnsupportedException

from twovyper.ast import names
from twovyper.ast import types
from twovyper.ast.arithmetic import Decimal
from twovyper.ast.nodes import VyperFunction, VyperInterface, VyperVar
from twovyper.ast.types import MapType, ArrayType, ContractType, InterfaceType

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt, StmtsAndExpr

from twovyper.translation.abstract import NodeTranslator
from twovyper.translation.arithmetic import ArithmeticTranslator
from twovyper.translation.balance import BalanceTranslator
from twovyper.translation.model import ModelTranslator
from twovyper.translation.state import StateTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.context import Context, interface_call_scope, program_scope, self_address_scope
from twovyper.translation.variable import TranslatedVar

from twovyper.translation import mangled
from twovyper.translation import helpers

from twovyper.verification import rules
from twovyper.verification.error import Via


class ExpressionTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.arithmetic_translator = ArithmeticTranslator(viper_ast, self.no_reverts)
        self.balance_translator = BalanceTranslator(viper_ast)
        self.model_translsator = ModelTranslator(viper_ast)
        self.state_translator = StateTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

        self._operations = {
            ast.Eq: self.viper_ast.EqCmp,
            ast.NotEq: self.viper_ast.NeCmp,
            ast.Lt: self.viper_ast.LtCmp,
            ast.LtE: self.viper_ast.LeCmp,
            ast.Gt: self.viper_ast.GtCmp,
            ast.GtE: self.viper_ast.GeCmp,
            ast.In: lambda l, r, pos: helpers.array_contains(viper_ast, l, r, pos),
            ast.NotIn: lambda l, r, pos: helpers.array_not_contains(viper_ast, l, r, pos),
            ast.And: self.viper_ast.And,
            ast.Or: self.viper_ast.Or,
            ast.Not: self.viper_ast.Not
        }

    @property
    def no_reverts(self) -> bool:
        return False

    @property
    def spec_translator(self):
        from twovyper.translation.specification import SpecificationTranslator
        return SpecificationTranslator(self.viper_ast)

    @property
    def function_translator(self):
        from twovyper.translation.function import FunctionTranslator
        return FunctionTranslator(self.viper_ast)

    def translate_Num(self, node: ast.Num, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if isinstance(node.n, int):
            if node.type == types.VYPER_BYTES32:
                bts = node.n.to_bytes(32, byteorder='big')
                elems = [self.viper_ast.IntLit(b, pos) for b in bts]
                return [], self.viper_ast.ExplicitSeq(elems, pos)
            else:
                return [], self.viper_ast.IntLit(node.n, pos)
        elif isinstance(node.n, Decimal):
            return [], self.viper_ast.IntLit(node.n.scaled_value, pos)
        else:
            assert False

    def translate_NameConstant(self, node: ast.NameConstant, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if node.value is True:
            return [], self.viper_ast.TrueLit(pos)
        elif node.value is False:
            return [], self.viper_ast.FalseLit(pos)
        else:
            assert False

    def translate_Name(self, node: ast.Name, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        if node.id == names.SELF and node.type == types.VYPER_ADDRESS:
            return [], ctx.self_address or helpers.self_address(self.viper_ast, pos)
        else:
            return [], ctx.all_vars[node.id].local_var(ctx, pos)

    def translate_BinOp(self, node: ast.BinOp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        left_stmts, left = self.translate(node.left, ctx)
        right_stmts, right = self.translate(node.right, ctx)

        at = self.arithmetic_translator
        res_stmts, res = at.binop(left, node.op, right, node.type, ctx, pos)
        return left_stmts + right_stmts + res_stmts, res

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

        stmts, expr = self.translate(node.operand, ctx)

        if types.is_numeric(node.type):
            res_stmts, res = self.arithmetic_translator.uop(node.op, expr, node.type, ctx, pos)
            stmts.extend(res_stmts)
        else:
            op = self.translate_operator(node.op)
            res = op(expr, pos)

        return stmts, res

    def translate_IfExp(self, node: ast.IfExp, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)
        test_stmts, test = self.translate(node.test, ctx)
        body_stmts, body = self.translate(node.body, ctx)
        orelse_stmts, orelse = self.translate(node.orelse, ctx)
        expr = self.viper_ast.CondExp(test, body, orelse, pos)
        return [*test_stmts, *body_stmts, *orelse_stmts], expr

    def translate_Compare(self, node: ast.Compare, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        assert len(node.ops) == 1

        left = node.left
        operator = node.ops[0]
        right = node.comparators[0]

        lhs_stmts, lhs = self.translate(left, ctx)
        op = self.translate_operator(operator)
        rhs_stmts, rhs = self.translate(right, ctx)
        stmts = lhs_stmts + rhs_stmts

        if isinstance(operator, ast.Eq):
            return stmts, self.type_translator.eq(node, lhs, rhs, left.type, ctx)
        elif isinstance(operator, ast.NotEq):
            return stmts, self.type_translator.neq(node, lhs, rhs, left.type, ctx)
        else:
            return stmts, op(lhs, rhs, pos)

    def translate_operator(self, operator):
        return self._operations[type(operator)]

    def translate_Attribute(self, node: ast.Attribute, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        # We don't support precise gas calculations, so we just return an unknown
        # non-negative value
        if node.attr == names.MSG_GAS and node.value.type == types.MSG_TYPE:
            gas_name = ctx.new_local_var_name('gas')
            gas_type = self.type_translator.translate(types.VYPER_UINT256, ctx)
            gas = self.viper_ast.LocalVarDecl(gas_name, gas_type, pos)
            ctx.new_local_vars.append(gas)

            zero = self.viper_ast.IntLit(0, pos)
            geq = self.viper_ast.GeCmp(gas.localVar(), zero, pos)
            return [self.viper_ast.Inhale(geq, pos)], gas.localVar()

        stmts, expr = self.translate(node.value, ctx)

        struct_type = node.value.type
        type = self.type_translator.translate(node.type, ctx)
        get = helpers.struct_get(self.viper_ast, expr, node.attr, type, struct_type, pos)
        return stmts, get

    def translate_Subscript(self, node: ast.Subscript, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        value_stmts, value = self.translate(node.value, ctx)
        index_stmts, index = self.translate(node.slice.value, ctx)
        stmts = []

        node_type = node.value.type
        if isinstance(node_type, MapType):
            key_type = self.type_translator.translate(node_type.key_type, ctx)
            value_type = self.type_translator.translate(node_type.value_type, ctx)
            call = helpers.map_get(self.viper_ast, value, index, key_type, value_type, pos)
        elif isinstance(node_type, ArrayType):
            if not self.no_reverts:
                stmts.append(self.type_translator.array_bounds_check(value, index, ctx))
            element_type = self.type_translator.translate(node_type.element_type, ctx)
            call = helpers.array_get(self.viper_ast, value, index, element_type, pos)

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
            elif name == names.ADDMOD or name == names.MULMOD:
                op1_stmts, op1 = self.translate(node.args[0], ctx)
                op2_stmts, op2 = self.translate(node.args[1], ctx)
                mod_stmts, mod = self.translate(node.args[2], ctx)

                cond = self.viper_ast.EqCmp(mod, self.viper_ast.IntLit(0, pos), pos)
                mod_stmts.append(self.fail_if(cond, [], ctx, pos))

                operation = self.viper_ast.Add if name == names.ADDMOD else self.viper_ast.Mul
                op_res = operation(op1, op2, pos)
                return op1_stmts + op2_stmts + mod_stmts, helpers.mod(self.viper_ast, op_res, mod, pos)
            elif name == names.SQRT:
                arg_stmts, arg = self.translate(node.args[0], ctx)
                zero = self.viper_ast.IntLit(0, pos)
                lt = self.viper_ast.LtCmp(arg, zero, pos)
                fail = self.fail_if(lt, [], ctx, pos)
                sqrt = helpers.sqrt(self.viper_ast, arg, pos)
                return [*arg_stmts, fail], sqrt
            elif name == names.FLOOR or name == names.CEIL:
                # Let s be the scaling factor, then
                #    floor(d) == d < 0 ? (d - (s - 1)) / s : d / s
                #    ceil(d)  == d < 0 ? d / s : (d + s - 1) / s
                arg_stmts, arg = self.translate(node.args[0], ctx)
                scaling_factor = node.args[0].type.scaling_factor

                if name == names.FLOOR:
                    expr = helpers.floor(self.viper_ast, arg, scaling_factor, pos)
                elif name == names.CEIL:
                    expr = helpers.ceil(self.viper_ast, arg, scaling_factor, pos)

                return arg_stmts, expr
            elif name == names.AS_WEI_VALUE:
                stmts, arg = self.translate(node.args[0], ctx)
                unit = node.args[1].s
                unit_pos = self.to_position(node.args[1], ctx)
                multiplier = next(v for k, v in names.ETHER_UNITS.items() if unit in k)
                multiplier_lit = self.viper_ast.IntLit(multiplier, unit_pos)
                res = self.viper_ast.Mul(arg, multiplier_lit, pos)

                if types.is_bounded(node.type):
                    oc = self.arithmetic_translator.check_under_overflow(res, node.type, ctx, pos)
                    stmts.extend(oc)

                return stmts, res
            elif name == names.AS_UNITLESS_NUMBER:
                return self.translate(node.args[0], ctx)
            elif name == names.LEN:
                arr_stmts, arr = self.translate(node.args[0], ctx)
                return arr_stmts, helpers.array_length(self.viper_ast, arr, pos)
            elif name == names.RANGE:
                if len(node.args) == 1:
                    start_stmts, start = [], self.viper_ast.IntLit(0, pos)
                    end_stmts, end = self.translate(node.args[0], ctx)
                else:
                    start_stmts, start = self.translate(node.args[0], ctx)
                    end_stmts, end = self.translate(node.args[1], ctx)

                range_func = helpers.range(self.viper_ast, start, end, pos)
                return [*start_stmts, *end_stmts], range_func
            elif name == names.CONCAT:
                concat_stmts, concats = zip(*[self.translate(arg, ctx) for arg in node.args])

                def concat(args):
                    arg, *tail = args
                    if not tail:
                        return arg
                    else:
                        return self.viper_ast.SeqAppend(arg, concat(tail), pos)

                return flatten(concat_stmts), concat(concats)
            elif name == names.CONVERT:
                from_type = node.args[0].type
                to_type = node.type

                arg_stmts, arg = self.translate(node.args[0], ctx)

                if isinstance(from_type, ArrayType) and from_type.element_type == types.VYPER_BYTE:
                    if from_type.size > 32:
                        raise UnsupportedException(node, 'Unsupported type converison.')

                    # If we convert a byte array to some type, we simply pad it to a bytes32 and
                    # proceed as if we had been given a bytes32
                    arg = helpers.pad32(self.viper_ast, arg, pos)
                    from_type = types.VYPER_BYTES32

                stmts = arg_stmts
                zero = self.viper_ast.IntLit(0, pos)
                one = self.viper_ast.IntLit(1, pos)

                zero_list = [0] * 32
                one_list = [0] * 31 + [1]
                zero_array = self.viper_ast.ExplicitSeq([self.viper_ast.IntLit(i, pos) for i in zero_list], pos)
                one_array = self.viper_ast.ExplicitSeq([self.viper_ast.IntLit(i, pos) for i in one_list], pos)

                with switch(from_type, to_type) as case:
                    from twovyper.utils import _
                    # If both types are equal (e.g. if we convert a literal) we simply
                    # return the argument
                    if case(_, _, where=from_type == to_type):
                        return stmts, arg
                    # --------------------- bool -> ? ---------------------
                    # If we convert from a bool we translate True as 1 and False as 0
                    elif case(types.VYPER_BOOL, types.VYPER_DECIMAL):
                        d_one = 1 * types.VYPER_DECIMAL.scaling_factor
                        d_one_lit = self.viper_ast.IntLit(d_one, pos)
                        return stmts, self.viper_ast.CondExp(arg, d_one_lit, zero, pos)
                    elif case(types.VYPER_BOOL, types.VYPER_BYTES32):
                        return stmts, self.viper_ast.CondExp(arg, one_array, zero_array, pos)
                    elif case(types.VYPER_BOOL, _):
                        return stmts, self.viper_ast.CondExp(arg, one, zero, pos)
                    # --------------------- ? -> bool ---------------------
                    # If we convert to a bool we check for zero
                    elif case(types.VYPER_BYTES32, types.VYPER_BOOL):
                        return stmts, self.viper_ast.NeCmp(arg, zero_array, pos)
                    elif case(_, types.VYPER_BOOL):
                        return stmts, self.viper_ast.NeCmp(arg, zero, pos)
                    # --------------------- decimal -> ? ---------------------
                    elif case(types.VYPER_DECIMAL, types.VYPER_INT128):
                        s = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
                        return stmts, helpers.div(self.viper_ast, arg, s, pos)
                    elif case(types.VYPER_DECIMAL, types.VYPER_UINT256):
                        s = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
                        res = helpers.div(self.viper_ast, arg, s, pos)
                        uc = self.arithmetic_translator.check_underflow(res, to_type, ctx, pos)
                        stmts.extend(uc)
                        return stmts, res
                    elif case(types.VYPER_DECIMAL, types.VYPER_BYTES32):
                        return stmts, helpers.convert_signed_int_to_bytes32(self.viper_ast, arg, pos)
                    # --------------------- int128 -> ? ---------------------
                    elif case(types.VYPER_INT128, types.VYPER_DECIMAL):
                        s = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
                        return stmts, self.viper_ast.Mul(arg, s, pos)
                    # When converting a signed number to an unsigned number we revert if
                    # the argument is negative
                    elif case(types.VYPER_INT128, types.VYPER_UINT256):
                        uc = self.arithmetic_translator.check_underflow(arg, to_type, ctx, pos)
                        stmts.extend(uc)
                        return stmts, arg
                    elif case(types.VYPER_INT128, types.VYPER_BYTES32):
                        return stmts, helpers.convert_signed_int_to_bytes32(self.viper_ast, arg, pos)
                    # --------------------- uint256 -> ? ---------------------
                    elif case(types.VYPER_UINT256, types.VYPER_DECIMAL):
                        s = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
                        res = self.viper_ast.Mul(arg, s, pos)
                        oc = self.arithmetic_translator.check_overflow(res, to_type, ctx, pos)
                        stmts.extend(oc)
                        return stmts, res
                    # If we convert an unsigned to a signed value we simply return
                    # the argument, given that it fits
                    elif case(types.VYPER_UINT256, types.VYPER_INT128):
                        oc = self.arithmetic_translator.check_overflow(arg, to_type, ctx, pos)
                        stmts.extend(oc)
                        return stmts, arg
                    elif case(types.VYPER_UINT256, types.VYPER_BYTES32):
                        return stmts, helpers.convert_unsigned_int_to_bytes32(self.viper_ast, arg, pos)
                    # --------------------- bytes32 -> ? ---------------------
                    elif case(types.VYPER_BYTES32, types.VYPER_DECIMAL) or case(types.VYPER_BYTES32, types.VYPER_INT128):
                        res = helpers.convert_bytes32_to_signed_int(self.viper_ast, arg, pos)
                        oc = self.arithmetic_translator.check_under_overflow(res, to_type, ctx, pos)
                        stmts.extend(oc)
                        return stmts, res
                    elif case(types.VYPER_BYTES32, types.VYPER_UINT256):
                        # uint256 and bytes32 have the same size, so no overflow check is necessary
                        return stmts, helpers.convert_bytes32_to_unsigned_int(self.viper_ast, arg, pos)
                    else:
                        raise UnsupportedException(node, 'Unsupported type converison.')
            elif name == names.KECCAK256:
                arg_stmts, arg = self.translate(node.args[0], ctx)
                return arg_stmts, helpers.array_keccak256(self.viper_ast, arg, pos)
            elif name == names.SHA256:
                arg_stmts, arg = self.translate(node.args[0], ctx)
                return arg_stmts, helpers.array_sha256(self.viper_ast, arg, pos)
            elif name == names.SELFDESTRUCT:
                arg_stmts, arg = self.translate(node.args[0], ctx)

                self_var = ctx.self_var.local_var(ctx)
                self_type = ctx.self_type

                val = self.viper_ast.TrueLit(pos)
                member = mangled.SELFDESTRUCT_FIELD
                type = self.type_translator.translate(self_type.member_types[member], ctx)
                sset = helpers.struct_set(self.viper_ast, self_var, val, member, type, self_type, pos)
                self_s_assign = self.viper_ast.LocalVarAssign(self_var, sset, pos)

                balance = self.balance_translator.get_balance(self_var, ctx, pos)
                sent = self.balance_translator.increase_sent(arg, balance, ctx, pos)

                zero = self.viper_ast.IntLit(0, pos)
                bset = self.balance_translator.set_balance(self_var, zero, ctx, pos)
                self_b_assign = self.viper_ast.LocalVarAssign(self_var, bset, pos)

                goto_return = self.viper_ast.Goto(ctx.return_label, pos)
                return [*arg_stmts, self_s_assign, sent, self_b_assign, goto_return], None
            elif name == names.ASSERT_MODIFIABLE:
                cond_stmts, cond = self.translate(node.args[0], ctx)
                not_cond = self.viper_ast.Not(cond, pos)
                fail = self.fail_if(not_cond, [], ctx, pos)
                return [*cond_stmts, fail], None
            elif name == names.SEND:
                to_stmts, to = self.translate(node.args[0], ctx)
                amount_stmts, amount = self.translate(node.args[1], ctx)
                call_stmts, _, expr = self._translate_external_call(node, to, amount, False, ctx)
                return [*to_stmts, *amount_stmts, *call_stmts], expr
            elif name == names.RAW_CALL:
                # Translate the callee address
                to_stmts, to = self.translate(node.args[0], ctx)
                # Translate the data expression (bytes)
                function_stmts, _ = self.translate(node.args[1], ctx)

                args_stmts = [*to_stmts, *function_stmts]
                amount = self.viper_ast.IntLit(0, pos)
                for kw in node.keywords:
                    arg_stmts, arg = self.translate(kw.value, ctx)
                    if kw.arg == names.RAW_CALL_VALUE:
                        amount = arg
                    args_stmts.extend(arg_stmts)

                call_stmts, _, call = self._translate_external_call(node, to, amount, False, ctx)
                return [*args_stmts, *call_stmts], call
            # This is a struct initializer
            elif len(node.args) == 1 and isinstance(node.args[0], ast.Dict):
                stmts = []
                exprs = {}
                for key, value in zip(node.args[0].keys, node.args[0].values):
                    value_stmts, value_expr = self.translate(value, ctx)
                    stmts.extend(value_stmts)
                    idx = node.type.member_indices[key.id]
                    exprs[idx] = value_expr

                init_args = [exprs[i] for i in range(len(exprs))]
                init = helpers.struct_init(self.viper_ast, init_args, node.type, pos)
                return stmts, init
            # This is a contract / interface initializer
            elif name in ctx.program.contracts or name in ctx.program.interfaces:
                return self.translate(node.args[0], ctx)
            else:
                raise UnsupportedException(node, "Unsupported function call")
        else:
            name = node.func.attr
            stmts, args = self.collect(self.translate(arg, ctx) for arg in node.args)
            rec_type = node.func.value.type

            if isinstance(rec_type, types.SelfType):
                call_stmts, res = self.function_translator.inline(node, args, ctx)
                return stmts + call_stmts, res
            elif isinstance(rec_type, (ContractType, InterfaceType)):
                to_stmts, to = self.translate(node.func.value, ctx)

                val_idx = first_index(lambda n: n.arg == names.RAW_CALL_VALUE, node.keywords)
                if val_idx >= 0:
                    amount_stmts, amount = self.translate(node.keywords[val_idx].value, ctx)
                    stmts.extend(amount_stmts)
                else:
                    amount = None

                if isinstance(rec_type, ContractType):
                    const = rec_type.function_modifiers[node.func.attr] == names.CONSTANT
                    call_stmts, _, res = self._translate_external_call(node, to, amount, const, ctx)
                    stmts.extend(call_stmts)
                else:
                    interface = ctx.program.interfaces[rec_type.name]
                    function = interface.functions[name]
                    const = function.is_constant()

                    # If the function is payable, but no ether is sent, revert
                    # If the function is not payable, but ether is sent, revert
                    zero = self.viper_ast.IntLit(0, pos)
                    if function.is_payable():
                        cond = self.viper_ast.LeCmp(amount, zero, pos) if amount else self.viper_ast.TrueLit(pos)
                    else:
                        cond = self.viper_ast.NeCmp(amount, zero, pos) if amount else self.viper_ast.FalseLit(pos)

                    stmts.append(self.fail_if(cond, [], ctx, pos))
                    known = (interface, function, args)
                    call_stmts, succ, res = self._translate_external_call(node, to, amount, const, ctx, known)
                    stmts.extend(call_stmts)

                return stmts, res
            elif node.func.value.id == names.LOG:
                event_name = mangled.event_name(name)
                pred_acc = self.viper_ast.PredicateAccess(args, event_name, pos)
                one = self.viper_ast.FullPerm(pos)
                pred_acc_pred = self.viper_ast.PredicateAccessPredicate(pred_acc, one, pos)
                stmts.append(self.viper_ast.Inhale(pred_acc_pred, pos))
                return self.seqn_with_info(stmts, f"Event: {name}"), None
            else:
                assert False

    def _translate_external_call(self,
                                 node: ast.Call,
                                 to: Expr,
                                 amount: Optional[Expr],
                                 constant: bool,
                                 ctx: Context,
                                 known: Tuple[VyperInterface, VyperFunction, List[Expr]] = []) -> Tuple[List[Stmt], Expr, Expr]:
        # Sends are translated as follows:
        #    - Evaluate arguments to and amount
        #    - Check that balance is sufficient (self.balance >= amount) else revert
        #    - Increment sent by amount
        #    - Subtract amount from self.balance (self.balance -= amount)
        #    - If in init, set old_self to self if this is the first public state
        #    - Assert checks and invariants
        #    - Create new old state which old in the invariants after the call refers to
        #    - Fail based on an unkown value (i.e. the call could fail)
        #    - The next steps are only necessary if the function is not constant:
        #       - Havoc self and contracts
        #       - Assume type assumptions for self
        #       - Assume invariants (where old refers to the state before send)
        #       - Create new old state which subsequent old expressions refer to
        #    - In the case of an interface call: Assume postconditions

        pos = self.to_position(node, ctx)
        self_var = ctx.self_var.local_var(ctx)

        if known:
            interface, function, args = known

        if amount:
            check = self.balance_translator.check_balance(amount, ctx, pos)
            sent = self.balance_translator.increase_sent(to, amount, ctx, pos)
            sub = self.balance_translator.decrease_balance(amount, ctx, pos)
            stmts = [check, sent, sub]
        else:
            stmts = []

        # In init set the old self state to the current self state, if this is the
        # first public state.
        if ctx.function.name == names.INIT:
            stmts.append(self.state_translator.check_first_public_state(ctx, True))

        check_assertions, modelt = self.model_translsator.save_variables(ctx, pos)
        for check in chain(ctx.function.checks, ctx.program.general_checks):
            check_stmts, check_cond = self.spec_translator.translate_check(check, ctx)
            via = [Via('check', check_cond.pos())]
            check_pos = self.to_position(node, ctx, rules.CALL_CHECK_FAIL, via, modelt)
            check_assertions.extend(check_stmts)
            check_assertions.append(self.viper_ast.Assert(check_cond, check_pos))

        inv_assertions = []
        for inv in ctx.program.invariants:
            # We ignore accessible because it only has to be checked in the end of
            # the function
            inv_stmts, cond = self.spec_translator.translate_invariant(inv, ctx, True)
            via = [Via('invariant', cond.pos())]
            call_pos = self.to_position(node, ctx, rules.CALL_INVARIANT_FAIL, via, modelt)
            inv_assertions.extend(inv_stmts)
            inv_assertions.append(self.viper_ast.Assert(cond, call_pos))

        assertions = [*check_assertions, *inv_assertions]

        copy_old = self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, ctx)

        send_fail_name = ctx.new_local_var_name('send_fail')
        send_fail = self.viper_ast.LocalVarDecl(send_fail_name, self.viper_ast.Bool)
        ctx.new_local_vars.append(send_fail)
        fail_cond = send_fail.localVar()
        msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
        msg_sender_eq = self.viper_ast.EqCmp(to, msg_sender)
        msg_sender_call_failed = helpers.msg_sender_call_fail_var(self.viper_ast).localVar()
        assume_msg_sender_call_failed = self.viper_ast.Inhale(self.viper_ast.Implies(msg_sender_eq, msg_sender_call_failed))
        fail = self.fail_if(fail_cond, [assume_msg_sender_call_failed], ctx, pos)

        # We forget about events by exhaling all permissions to the event predicates, i.e.
        # for all event predicates e we do
        #   exhale forall arg0, arg1, ... :: perm(e(arg0, arg1, ...)) > none ==> acc(e(...), perm(e(...)))
        # We use an implication with a '> none' because of a bug in Carbon (TODO: issue #171) where it isn't possible
        # to exhale no permissions under a quantifier.
        event_exhales = []
        for event in ctx.program.events.values():
            event_name = mangled.event_name(event.name)
            types = [self.type_translator.translate(arg, ctx) for arg in event.type.arg_types]
            args = [self.viper_ast.LocalVarDecl(f'$arg{idx}', type, pos) for idx, type in enumerate(types)]
            local_args = [arg.localVar() for arg in args]
            pa = self.viper_ast.PredicateAccess(local_args, event_name, pos)
            perm = self.viper_ast.CurrentPerm(pa, pos)
            pap = self.viper_ast.PredicateAccessPredicate(pa, perm, pos)
            none = self.viper_ast.NoPerm(pos)
            impl = self.viper_ast.Implies(self.viper_ast.GtCmp(perm, none, pos), pap)
            trigger = self.viper_ast.Trigger([pa], pos)
            forall = self.viper_ast.Forall(args, [trigger], impl, pos)
            event_exhales.append(self.viper_ast.Exhale(forall, pos))

        if not constant:
            # Save the values of to, amount, and args, as self could be changed by reentrancy
            save_vars = []
            if known:

                def new_var(var, name='v'):
                    var_name = ctx.new_local_var_name(name)
                    var_decl = self.viper_ast.LocalVarDecl(var_name, var.typ(), pos)
                    ctx.new_local_vars.append(var_decl)
                    save_vars.append(self.viper_ast.LocalVarAssign(var_decl.localVar(), var))
                    return var_decl.localVar()

                to = new_var(to, 'to')
                if amount:
                    amount = new_var(amount, 'amount')
                # Force evaluation at this point
                args = list(map(new_var, args))

            # Havoc state
            havocs = self.state_translator.havoc_state(ctx.current_state, ctx, pos)

            call = [fail, *copy_old, *event_exhales, *save_vars, *havocs]

            type_ass = self.type_translator.type_assumptions(self_var, ctx.self_type, ctx)
            assume_type_ass = [self.viper_ast.Inhale(inv) for inv in type_ass]
            type_seq = self.seqn_with_info(assume_type_ass, "Assume type assumptions")

            assume_posts = []
            for post in ctx.program.transitive_postconditions:
                post_stmts, post_expr = self.spec_translator.translate_postcondition(post, ctx)
                ppos = self.to_position(post, ctx, rules.INHALE_POSTCONDITION_FAIL)
                assume_posts.extend(post_stmts)
                assume_posts.append(self.viper_ast.Inhale(post_expr, ppos))

            post_seq = self.seqn_with_info(assume_posts, "Assume transitive postconditions")

            assume_invs = []
            for inv in ctx.unchecked_invariants():
                assume_invs.append(self.viper_ast.Inhale(inv))

            for inv in ctx.program.invariants:

                inv_stmts, cond = self.spec_translator.translate_invariant(inv, ctx, True)
                ipos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                assume_invs.extend(inv_stmts)
                assume_invs.append(self.viper_ast.Inhale(cond, ipos))

            inv_seq = self.seqn_with_info(assume_invs, "Assume invariants")

            new_state = [*type_seq, *post_seq, *inv_seq]
        else:
            call = [fail, *copy_old, *event_exhales]
            new_state = []

        if node.type:
            ret_name = ctx.new_local_var_name('raw_ret')
            ret_type = self.type_translator.translate(node.type, ctx)
            ret_var = self.viper_ast.LocalVarDecl(ret_name, ret_type, pos)
            ctx.new_local_vars.append(ret_var)
            return_value = ret_var.localVar()
            type_ass = self.type_translator.type_assumptions(return_value, node.type, ctx)
            return_stmts = [self.viper_ast.Inhale(ass) for ass in type_ass]
        else:
            return_value = None
            return_stmts = []

        success = self.viper_ast.Not(fail_cond, pos)

        if known:
            assume_itf = self._assume_interface_specifications
            amount = amount or self.viper_ast.IntLit(0)
            itf = assume_itf(node, interface, function, args, to, amount, success, return_value, ctx)
        else:
            itf = []

        return stmts + assertions + call + new_state + return_stmts + itf + copy_old, success, return_value

    def _assume_interface_specifications(self,
                                         node: ast.AST,
                                         interface: VyperInterface,
                                         function: VyperFunction,
                                         args: List[Expr],
                                         to: Expr,
                                         amount: Expr,
                                         succ: Expr,
                                         res: Optional[Expr],
                                         ctx: Context) -> List[Stmt]:
        with interface_call_scope(ctx):
            body = []

            # Define new msg variable
            msg_name = ctx.inline_prefix + mangled.MSG
            msg_var = TranslatedVar(names.MSG, msg_name, types.MSG_TYPE, self.viper_ast)
            ctx.locals[names.MSG] = msg_var
            ctx.new_local_vars.append(msg_var.var_decl(ctx))

            # Assume msg.sender == self and msg.value == amount
            msg = msg_var.local_var(ctx)
            svytype = types.MSG_TYPE.member_types[names.MSG_SENDER]
            svitype = self.type_translator.translate(svytype, ctx)
            msg_sender = helpers.struct_get(self.viper_ast, msg, names.MSG_SENDER, svitype, types.MSG_TYPE)
            self_address = helpers.self_address(self.viper_ast)
            body.append(self.viper_ast.Inhale(self.viper_ast.EqCmp(msg_sender, self_address)))

            vvytype = types.MSG_TYPE.member_types[names.MSG_VALUE]
            vvitype = self.type_translator.translate(vvytype, ctx)
            msg_value = helpers.struct_get(self.viper_ast, msg, names.MSG_VALUE, vvitype, types.MSG_TYPE)
            body.append(self.viper_ast.Inhale(self.viper_ast.EqCmp(msg_value, amount)))

            # Add arguments to local vars, assign passed args
            for (name, var), arg in zip(function.args.items(), args):
                apos = arg.pos()
                arg_var = self._translate_var(var, ctx)
                ctx.locals[name] = arg_var
                ctx.new_local_vars.append(arg_var.var_decl(ctx))
                body.append(self.viper_ast.LocalVarAssign(arg_var.local_var(ctx), arg, apos))

            # Add result variable
            if function.type.return_type:
                res_name = ctx.inline_prefix + mangled.RESULT_VAR
                ctx.result_var = TranslatedVar(names.RESULT, res_name, function.type.return_type, self.viper_ast, res.pos())
                ctx.new_local_vars.append(ctx.result_var.var_decl(ctx, res.pos()))
                body.append(self.viper_ast.LocalVarAssign(ctx.result_var.local_var(res.pos()), res, res.pos()))

            # Add success variable
            succ_name = ctx.inline_prefix + mangled.SUCCESS_VAR
            succ_var = TranslatedVar(names.SUCCESS, succ_name, types.VYPER_BOOL, self.viper_ast, succ.pos())
            ctx.new_local_vars.append(succ_var.var_decl(ctx))
            ctx.success_var = succ_var
            body.append(self.viper_ast.LocalVarAssign(succ_var.local_var(ctx), succ, succ.pos()))

            translate = self.spec_translator.translate_postcondition
            pos = self.to_position(node, ctx, rules.INHALE_INTERFACE_FAIL)

            with program_scope(interface, ctx):
                with self_address_scope(to, ctx):
                    postconditions = chain(function.postconditions, interface.general_postconditions)
                    stmts, exprs = self.collect(translate(post, ctx) for post in postconditions)
                    body.extend(stmts)
                    body.extend(self.viper_ast.Inhale(expr, pos) for expr in exprs)

            if ctx.program.config.has_option(names.CONFIG_TRUST_CASTS):
                return body
            else:
                implements = helpers.implements(self.viper_ast, to, interface.name, ctx, pos)
                return [self.viper_ast.If(implements, body, [], pos)]

    def _translate_var(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        name = mangled.local_var_name(ctx.inline_prefix, var.name)
        return TranslatedVar(var.name, name, var.type, self.viper_ast, pos)
