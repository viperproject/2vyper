"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from itertools import chain
from typing import List, Optional, Tuple

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.arithmetic import Decimal
from twovyper.ast.nodes import VyperFunction, VyperInterface, VyperVar, VyperEvent
from twovyper.ast.types import MapType, ArrayType, StructType, AddressType, ContractType, InterfaceType

from twovyper.exceptions import UnsupportedException

from twovyper.translation import mangled
from twovyper.translation import helpers

from twovyper.translation.context import Context
from twovyper.translation.abstract import NodeTranslator
from twovyper.translation.allocation import AllocationTranslator
from twovyper.translation.arithmetic import ArithmeticTranslator
from twovyper.translation.balance import BalanceTranslator
from twovyper.translation.model import ModelTranslator
from twovyper.translation.resource import ResourceTranslator
from twovyper.translation.state import StateTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.utils import switch, first_index

from twovyper.verification import rules
from twovyper.verification.error import Via

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


class ExpressionTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.allocation_translator = AllocationTranslator(viper_ast)
        self.arithmetic_translator = ArithmeticTranslator(viper_ast, self.no_reverts)
        self.balance_translator = BalanceTranslator(viper_ast)
        self.model_translator = ModelTranslator(viper_ast)
        self.resource_translator = ResourceTranslator(viper_ast)
        self.state_translator = StateTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

        self._bool_ops = {
            ast.BoolOperator.AND: self.viper_ast.And,
            ast.BoolOperator.OR: self.viper_ast.Or,
            ast.BoolOperator.IMPLIES: self.viper_ast.Implies
        }

        self._comparison_ops = {
            ast.ComparisonOperator.LT: self.viper_ast.LtCmp,
            ast.ComparisonOperator.LTE: self.viper_ast.LeCmp,
            ast.ComparisonOperator.GTE: self.viper_ast.GeCmp,
            ast.ComparisonOperator.GT: self.viper_ast.GtCmp
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

    def translate_Num(self, node: ast.Num, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        if isinstance(node.n, int):
            if node.type == types.VYPER_BYTES32:
                bts = node.n.to_bytes(32, byteorder='big')
                elems = [self.viper_ast.IntLit(b, pos) for b in bts]
                return self.viper_ast.ExplicitSeq(elems, pos)
            else:
                return self.viper_ast.IntLit(node.n, pos)
        elif isinstance(node.n, Decimal):
            return self.viper_ast.IntLit(node.n.scaled_value, pos)
        else:
            assert False

    def translate_Bool(self, node: ast.Bool, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        return self.viper_ast.TrueLit(pos) if node.value else self.viper_ast.FalseLit(pos)

    def translate_Name(self, node: ast.Name, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        if node.id == names.SELF and node.type == types.VYPER_ADDRESS:
            return ctx.self_address or helpers.self_address(self.viper_ast, pos)
        elif ctx.inside_inline_analysis and node.id not in ctx.all_vars:
            # Generate new local variable
            variable_name = node.id
            mangled_name = ctx.new_local_var_name(variable_name)
            var = TranslatedVar(variable_name, mangled_name, node.type, self.viper_ast, pos)
            ctx.locals[variable_name] = var
            ctx.new_local_vars.append(var.var_decl(ctx))
        return ctx.all_vars[node.id].local_var(ctx, pos)

    def translate_ArithmeticOp(self, node: ast.ArithmeticOp, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        left = self.translate(node.left, res, ctx)
        right = self.translate(node.right, res, ctx)

        return self.arithmetic_translator.arithmetic_op(left, node.op, right, node.type, res, ctx, pos)

    def translate_BoolOp(self, node: ast.BoolOp, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        left = self.translate(node.left, res, ctx)
        op = self._bool_ops[node.op]
        right = self.translate(node.right, res, ctx)

        return op(left, right, pos)

    def translate_Not(self, node: ast.Not, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        operand = self.translate(node.operand, res, ctx)
        return self.viper_ast.Not(operand, pos)

    def translate_UnaryArithmeticOp(self, node: ast.UnaryArithmeticOp, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        operand = self.translate(node.operand, res, ctx)
        return self.arithmetic_translator.unary_arithmetic_op(node.op, operand, node.type, res, ctx, pos)

    def translate_IfExpr(self, node: ast.IfExpr, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        test = self.translate(node.test, res, ctx)
        body = self.translate(node.body, res, ctx)
        orelse = self.translate(node.orelse, res, ctx)
        return self.viper_ast.CondExp(test, body, orelse, pos)

    def translate_Comparison(self, node: ast.Comparison, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        lhs = self.translate(node.left, res, ctx)
        op = self._comparison_ops[node.op]
        rhs = self.translate(node.right, res, ctx)
        return op(lhs, rhs, pos)

    def translate_Containment(self, node: ast.Containment, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        value = self.translate(node.value, res, ctx)
        list = self.translate(node.list, res, ctx)

        if node.op == ast.ContainmentOperator.IN:
            return helpers.array_contains(self.viper_ast, value, list, pos)
        elif node.op == ast.ContainmentOperator.NOT_IN:
            return helpers.array_not_contains(self.viper_ast, value, list, pos)
        else:
            assert False

    def translate_Equality(self, node: ast.Equality, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        lhs = self.translate(node.left, res, ctx)
        rhs = self.translate(node.right, res, ctx)

        if node.op == ast.EqualityOperator.EQ:
            return self.type_translator.eq(lhs, rhs, node.left.type, ctx, pos)
        elif node.op == ast.EqualityOperator.NEQ:
            return self.type_translator.neq(lhs, rhs, node.left.type, ctx, pos)
        else:
            assert False

    def translate_operator(self, operator):
        return self._operations[type(operator)]

    def translate_Attribute(self, node: ast.Attribute, res: List[Stmt], ctx: Context) -> Expr:
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
            res.append(self.viper_ast.Inhale(geq, pos))

            return gas.localVar()

        expr = self.translate(node.value, res, ctx)

        if isinstance(node.value.type, StructType):
            # The value is a struct
            struct_type = node.value.type
            struct = expr
        else:
            # The value is an address
            struct_type = AddressType()
            contracts = ctx.current_state[mangled.CONTRACTS].local_var(ctx)
            key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
            value_type = helpers.struct_type(self.viper_ast)
            struct = helpers.map_get(self.viper_ast, contracts, expr, key_type, value_type)

        type = self.type_translator.translate(node.type, ctx)
        get = helpers.struct_get(self.viper_ast, struct, node.attr, type, struct_type, pos)
        return get

    def translate_Subscript(self, node: ast.Subscript, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        value = self.translate(node.value, res, ctx)
        index = self.translate(node.index, res, ctx)

        node_type = node.value.type
        if isinstance(node_type, MapType):
            key_type = self.type_translator.translate(node_type.key_type, ctx)
            value_type = self.type_translator.translate(node_type.value_type, ctx)
            call = helpers.map_get(self.viper_ast, value, index, key_type, value_type, pos)
        elif isinstance(node_type, ArrayType):
            if not self.no_reverts:
                self.type_translator.array_bounds_check(value, index, res, ctx)
            element_type = self.type_translator.translate(node_type.element_type, ctx)
            call = helpers.array_get(self.viper_ast, value, index, element_type, pos)

        return call

    def translate_List(self, node: ast.List, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        if not node.elements:
            type = self.type_translator.translate(node.type.element_type, ctx)
            return self.viper_ast.EmptySeq(type, pos)
        else:
            elems = [self.translate(e, res, ctx) for e in node.elements]
            return self.viper_ast.ExplicitSeq(elems, pos)

    def translate_Str(self, node: ast.Str, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        if not node.s:
            type = self.type_translator.translate(node.type.element_type, ctx)
            return self.viper_ast.EmptySeq(type, pos)
        else:
            elems = [self.viper_ast.IntLit(e, pos) for e in bytes(node.s, 'utf-8')]
            return self.viper_ast.ExplicitSeq(elems, pos)

    def translate_Bytes(self, node: ast.Bytes, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        if not node.s:
            type = self.type_translator.translate(node.type.element_type, ctx)
            return self.viper_ast.EmptySeq(type, pos)
        else:
            elems = [self.viper_ast.IntLit(e, pos) for e in node.s]
            return self.viper_ast.ExplicitSeq(elems, pos)

    def translate_FunctionCall(self, node: ast.FunctionCall, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        name = node.name
        is_min = (name == names.MIN)
        is_max = (name == names.MAX)
        if is_min or is_max:
            lhs = self.translate(node.args[0], res, ctx)
            rhs = self.translate(node.args[1], res, ctx)
            op = self.viper_ast.GtCmp if is_max else self.viper_ast.LtCmp
            comp = op(lhs, rhs, pos)
            return self.viper_ast.CondExp(comp, lhs, rhs, pos)
        elif name == names.ADDMOD or name == names.MULMOD:
            op1 = self.translate(node.args[0], res, ctx)
            op2 = self.translate(node.args[1], res, ctx)
            mod = self.translate(node.args[2], res, ctx)

            cond = self.viper_ast.EqCmp(mod, self.viper_ast.IntLit(0, pos), pos)
            self.fail_if(cond, [], res, ctx, pos)

            operation = self.viper_ast.Add if name == names.ADDMOD else self.viper_ast.Mul
            op_res = operation(op1, op2, pos)
            return helpers.mod(self.viper_ast, op_res, mod, pos)
        elif name == names.SQRT:
            arg = self.translate(node.args[0], res, ctx)
            zero = self.viper_ast.IntLit(0, pos)
            lt = self.viper_ast.LtCmp(arg, zero, pos)
            self.fail_if(lt, [], res, ctx, pos)
            sqrt = helpers.sqrt(self.viper_ast, arg, pos)
            return sqrt
        elif name == names.FLOOR or name == names.CEIL:
            # Let s be the scaling factor, then
            #    floor(d) == d < 0 ? (d - (s - 1)) / s : d / s
            #    ceil(d)  == d < 0 ? d / s : (d + s - 1) / s
            arg = self.translate(node.args[0], res, ctx)
            scaling_factor = node.args[0].type.scaling_factor

            if name == names.FLOOR:
                expr = helpers.floor(self.viper_ast, arg, scaling_factor, pos)
            elif name == names.CEIL:
                expr = helpers.ceil(self.viper_ast, arg, scaling_factor, pos)

            return expr
        elif name == names.SHIFT:
            arg = self.translate(node.args[0], res, ctx)
            shift = self.translate(node.args[1], res, ctx)
            return helpers.shift(self.viper_ast, arg, shift, pos)
        elif name in [names.BITWISE_AND, names.BITWISE_OR, names.BITWISE_XOR]:
            a = self.translate(node.args[0], res, ctx)
            b = self.translate(node.args[1], res, ctx)

            funcs = {
                names.BITWISE_AND: helpers.bitwise_and,
                names.BITWISE_OR: helpers.bitwise_or,
                names.BITWISE_XOR: helpers.bitwise_xor
            }

            return funcs[name](self.viper_ast, a, b, pos)
        elif name == names.BITWISE_NOT:
            arg = self.translate(node.args[0], res, ctx)
            return helpers.bitwise_not(self.viper_ast, arg, pos)
        elif name == names.AS_WEI_VALUE:
            arg = self.translate(node.args[0], res, ctx)
            unit = node.args[1].s
            unit_pos = self.to_position(node.args[1], ctx)
            multiplier = next(v for k, v in names.ETHER_UNITS.items() if unit in k)
            multiplier_lit = self.viper_ast.IntLit(multiplier, unit_pos)
            num = self.viper_ast.Mul(arg, multiplier_lit, pos)

            if types.is_bounded(node.type):
                self.arithmetic_translator.check_under_overflow(num, node.type, res, ctx, pos)

            return num
        elif name == names.AS_UNITLESS_NUMBER:
            return self.translate(node.args[0], res, ctx)
        elif name == names.LEN:
            arr = self.translate(node.args[0], res, ctx)
            return helpers.array_length(self.viper_ast, arr, pos)
        elif name == names.RANGE:
            if len(node.args) == 1:
                start = self.viper_ast.IntLit(0, pos)
                end = self.translate(node.args[0], res, ctx)
            else:
                start = self.translate(node.args[0], res, ctx)
                end = self.translate(node.args[1], res, ctx)

            return helpers.range(self.viper_ast, start, end, pos)
        elif name == names.CONCAT:
            concats = [self.translate(arg, res, ctx) for arg in node.args]

            def concat(args):
                arg, *tail = args
                if not tail:
                    return arg
                else:
                    return self.viper_ast.SeqAppend(arg, concat(tail), pos)

            return concat(concats)
        elif name == names.CONVERT:
            from_type = node.args[0].type
            to_type = node.type

            arg = self.translate(node.args[0], res, ctx)

            if isinstance(from_type, ArrayType) and from_type.element_type == types.VYPER_BYTE:
                if from_type.size > 32:
                    raise UnsupportedException(node, 'Unsupported type converison.')

                # If we convert a byte array to some type, we simply pad it to a bytes32 and
                # proceed as if we had been given a bytes32
                arg = helpers.pad32(self.viper_ast, arg, pos)
                from_type = types.VYPER_BYTES32

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
                    return arg
                # --------------------- bool -> ? ---------------------
                # If we convert from a bool we translate True as 1 and False as 0
                elif case(types.VYPER_BOOL, types.VYPER_DECIMAL):
                    d_one = 1 * types.VYPER_DECIMAL.scaling_factor
                    d_one_lit = self.viper_ast.IntLit(d_one, pos)
                    return self.viper_ast.CondExp(arg, d_one_lit, zero, pos)
                elif case(types.VYPER_BOOL, types.VYPER_BYTES32):
                    return self.viper_ast.CondExp(arg, one_array, zero_array, pos)
                elif case(types.VYPER_BOOL, _):
                    return self.viper_ast.CondExp(arg, one, zero, pos)
                # --------------------- ? -> bool ---------------------
                # If we convert to a bool we check for zero
                elif case(types.VYPER_BYTES32, types.VYPER_BOOL):
                    return self.viper_ast.NeCmp(arg, zero_array, pos)
                elif case(_, types.VYPER_BOOL):
                    return self.viper_ast.NeCmp(arg, zero, pos)
                # --------------------- decimal -> ? ---------------------
                elif case(types.VYPER_DECIMAL, types.VYPER_INT128):
                    s = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
                    return helpers.div(self.viper_ast, arg, s, pos)
                elif case(types.VYPER_DECIMAL, types.VYPER_UINT256):
                    s = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
                    div = helpers.div(self.viper_ast, arg, s, pos)
                    self.arithmetic_translator.check_underflow(div, to_type, res, ctx, pos)
                    return div
                elif case(types.VYPER_DECIMAL, types.VYPER_BYTES32):
                    return helpers.convert_signed_int_to_bytes32(self.viper_ast, arg, pos)
                # --------------------- int128 -> ? ---------------------
                elif case(types.VYPER_INT128, types.VYPER_DECIMAL):
                    s = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
                    return self.viper_ast.Mul(arg, s, pos)
                # When converting a signed number to an unsigned number we revert if
                # the argument is negative
                elif case(types.VYPER_INT128, types.VYPER_UINT256):
                    self.arithmetic_translator.check_underflow(arg, to_type, res, ctx, pos)
                    return arg
                elif case(types.VYPER_INT128, types.VYPER_BYTES32):
                    return helpers.convert_signed_int_to_bytes32(self.viper_ast, arg, pos)
                # --------------------- uint256 -> ? ---------------------
                elif case(types.VYPER_UINT256, types.VYPER_DECIMAL):
                    s = self.viper_ast.IntLit(types.VYPER_DECIMAL.scaling_factor, pos)
                    mul = self.viper_ast.Mul(arg, s, pos)
                    self.arithmetic_translator.check_overflow(mul, to_type, res, ctx, pos)
                    return mul
                # If we convert an unsigned to a signed value we simply return
                # the argument, given that it fits
                elif case(types.VYPER_UINT256, types.VYPER_INT128):
                    self.arithmetic_translator.check_overflow(arg, to_type, res, ctx, pos)
                    return arg
                elif case(types.VYPER_UINT256, types.VYPER_BYTES32):
                    return helpers.convert_unsigned_int_to_bytes32(self.viper_ast, arg, pos)
                # --------------------- bytes32 -> ? ---------------------
                elif case(types.VYPER_BYTES32, types.VYPER_DECIMAL) or case(types.VYPER_BYTES32, types.VYPER_INT128):
                    i = helpers.convert_bytes32_to_signed_int(self.viper_ast, arg, pos)
                    self.arithmetic_translator.check_under_overflow(i, to_type, res, ctx, pos)
                    return i
                elif case(types.VYPER_BYTES32, types.VYPER_UINT256):
                    # uint256 and bytes32 have the same size, so no overflow check is necessary
                    return helpers.convert_bytes32_to_unsigned_int(self.viper_ast, arg, pos)
                else:
                    raise UnsupportedException(node, 'Unsupported type converison.')
        elif name == names.KECCAK256:
            arg = self.translate(node.args[0], res, ctx)
            return helpers.keccak256(self.viper_ast, arg, pos)
        elif name == names.SHA256:
            arg = self.translate(node.args[0], res, ctx)
            return helpers.sha256(self.viper_ast, arg, pos)
        elif name == names.BLOCKHASH:
            arg = self.translate(node.args[0], res, ctx)

            block = ctx.block_var.local_var(ctx)
            number_type = self.type_translator.translate(types.BLOCK_TYPE.member_types[names.BLOCK_NUMBER], ctx)
            block_number = helpers.struct_get(self.viper_ast, block, names.BLOCK_NUMBER, number_type, types.BLOCK_TYPE, pos)

            # Only the last 256 blocks (before the current block) are available in blockhash, else we revert
            lt = self.viper_ast.LtCmp(arg, block_number, pos)
            last_256 = self.viper_ast.Sub(block_number, self.viper_ast.IntLit(256, pos), pos)
            ge = self.viper_ast.GeCmp(arg, last_256, pos)
            cond = self.viper_ast.Not(self.viper_ast.And(lt, ge, pos), pos)
            self.fail_if(cond, [], res, ctx, pos)

            return helpers.blockhash(self.viper_ast, arg, ctx, pos)
        elif name == names.METHOD_ID:
            arg = self.translate(node.args[0], res, ctx)
            return helpers.method_id(self.viper_ast, arg, node.type.size, pos)
        elif name == names.ECRECOVER:
            args = [self.translate(arg, res, ctx) for arg in node.args]
            return helpers.ecrecover(self.viper_ast, args, pos)
        elif name == names.ECADD or name == names.ECMUL:
            args = [self.translate(arg, res, ctx) for arg in node.args]
            fail_var_name = ctx.new_local_var_name('$fail')
            fail_var_decl = self.viper_ast.LocalVarDecl(fail_var_name, self.viper_ast.Bool, pos)
            ctx.new_local_vars.append(fail_var_decl)
            fail_var = fail_var_decl.localVar()
            self.fail_if(fail_var, [], res, ctx, pos)
            if name == names.ECADD:
                return helpers.ecadd(self.viper_ast, args, pos)
            else:
                return helpers.ecmul(self.viper_ast, args, pos)
        elif name == names.SELFDESTRUCT:
            to = self.translate(node.args[0], res, ctx)

            self_var = ctx.self_var.local_var(ctx)
            self_type = ctx.self_type

            balance = self.balance_translator.get_balance(self_var, ctx, pos)

            if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
                resource = self.resource_translator.resource(names.WEI, [], ctx)
                self.allocation_translator.deallocate(node, resource, to, balance, res, ctx, pos)

            val = self.viper_ast.TrueLit(pos)
            member = mangled.SELFDESTRUCT_FIELD
            type = self.type_translator.translate(self_type.member_types[member], ctx)
            sset = helpers.struct_set(self.viper_ast, self_var, val, member, type, self_type, pos)
            res.append(self.viper_ast.LocalVarAssign(self_var, sset, pos))

            self.balance_translator.increase_sent(to, balance, res, ctx, pos)

            zero = self.viper_ast.IntLit(0, pos)
            bset = self.balance_translator.set_balance(self_var, zero, ctx, pos)
            res.append(self.viper_ast.LocalVarAssign(self_var, bset, pos))

            res.append(self.viper_ast.Goto(ctx.return_label, pos))
            return None
        elif name == names.ASSERT_MODIFIABLE:
            cond = self.translate(node.args[0], res, ctx)
            not_cond = self.viper_ast.Not(cond, pos)
            self.fail_if(not_cond, [], res, ctx, pos)
            return None
        elif name == names.SEND:
            to = self.translate(node.args[0], res, ctx)
            amount = self.translate(node.args[1], res, ctx)
            _, expr = self._translate_external_call(node, to, amount, False, res, ctx)
            return expr
        elif name == names.RAW_CALL:
            # Translate the callee address
            to = self.translate(node.args[0], res, ctx)
            # Translate the data expression (bytes)
            _ = self.translate(node.args[1], res, ctx)

            amount = self.viper_ast.IntLit(0, pos)
            for kw in node.keywords:
                arg = self.translate(kw.value, res, ctx)
                if kw.name == names.RAW_CALL_VALUE:
                    amount = arg

            _, call = self._translate_external_call(node, to, amount, False, res, ctx)
            return call
        elif name == names.RAW_LOG:
            _ = self.translate(node.args[0], res, ctx)
            _ = self.translate(node.args[1], res, ctx)

            # Since we don't know what raw_log logs, any event could have been emitted.
            # Therefore we create a fresh var and do
            # if var == 0:
            #    log.event1(...)
            # elif var == 1:
            #    log.event2(...)
            # ...
            # for all events to indicate that at most one event has been emitted.

            var_name = ctx.new_local_var_name('$a')
            var_decl = self.viper_ast.LocalVarDecl(var_name, self.viper_ast.Int, pos)
            ctx.new_local_vars.append(var_decl)
            var = var_decl.localVar()
            for idx, event in enumerate(ctx.program.events.values()):
                condition = self.viper_ast.EqCmp(var, self.viper_ast.IntLit(idx, pos), pos)

                args = []
                for arg_type in event.type.arg_types:
                    arg_name = ctx.new_local_var_name('$arg')
                    arg_type = self.type_translator.translate(arg_type, ctx)
                    arg = self.viper_ast.LocalVarDecl(arg_name, arg_type, pos)
                    ctx.new_local_vars.append(arg)
                    args.append(arg.localVar())

                log_event = []
                self._log_event(event, args, log_event, ctx, pos)
                res.append(self.viper_ast.If(condition, log_event, [], pos))

            return None
        elif name == names.CREATE_FORWARDER_TO:
            at = self.translate(node.args[0], res, ctx)
            if node.keywords:
                amount = self.translate(node.keywords[0].value, res, ctx)
                self.balance_translator.check_balance(amount, res, ctx, pos)
                self.balance_translator.increase_sent(at, amount, res, ctx, pos)
                self.balance_translator.decrease_balance(amount, res, ctx, pos)

            new_name = ctx.new_local_var_name('$new')
            type = self.type_translator.translate(node.type, ctx)
            new_var_decl = self.viper_ast.LocalVarDecl(new_name, type, pos)
            ctx.new_local_vars.append(new_var_decl)
            new_var = new_var_decl.localVar()

            eq_zero = self.viper_ast.EqCmp(new_var, self.viper_ast.IntLit(0, pos), pos)
            self.fail_if(eq_zero, [], res, ctx, pos)

            return new_var
        # This is a struct initializer
        elif len(node.args) == 1 and isinstance(node.args[0], ast.Dict):
            exprs = {}
            for key, value in zip(node.args[0].keys, node.args[0].values):
                value_expr = self.translate(value, res, ctx)
                idx = node.type.member_indices[key.id]
                exprs[idx] = value_expr

            init_args = [exprs[i] for i in range(len(exprs))]
            init = helpers.struct_init(self.viper_ast, init_args, node.type, pos)
            return init
        # This is a contract / interface initializer
        elif name in ctx.program.contracts or name in ctx.program.interfaces:
            return self.translate(node.args[0], res, ctx)
        elif name in names.GHOST_STATEMENTS:
            return self.spec_translator.translate_ghost_statement(node, res, ctx)
        else:
            assert False

    def translate_ReceiverCall(self, node: ast.ReceiverCall, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        name = node.name
        args = [self.translate(arg, res, ctx) for arg in node.args]
        rec_type = node.receiver.type

        if isinstance(rec_type, types.SelfType):
            call_result = self.function_translator.inline(node, args, res, ctx)
            return call_result
        elif isinstance(rec_type, (ContractType, InterfaceType)):
            to = self.translate(node.receiver, res, ctx)

            val_idx = first_index(lambda n: n.name == names.RAW_CALL_VALUE, node.keywords)
            if val_idx >= 0:
                amount = self.translate(node.keywords[val_idx].value, res, ctx)
            else:
                amount = None

            if isinstance(rec_type, ContractType):
                const = rec_type.function_modifiers[node.name] == names.CONSTANT
                _, call_result = self._translate_external_call(node, to, amount, const, res, ctx)
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

                self.fail_if(cond, [], res, ctx, pos)
                known = (interface, function, args)
                succ, call_result = self._translate_external_call(node, to, amount, const, res, ctx, known)

            return call_result
        elif node.receiver.id == names.LOG:
            event = ctx.program.events[name]
            self._log_event(event, args, res, ctx, pos)
            return None
        else:
            assert False

    def _log_event(self, event: VyperEvent, args: List[Expr], res: List[Stmt], ctx: Context, pos=None):
        event_name = mangled.event_name(event.name)
        pred_acc = self.viper_ast.PredicateAccess(args, event_name, pos)
        one = self.viper_ast.FullPerm(pos)
        pred_acc_pred = self.viper_ast.PredicateAccessPredicate(pred_acc, one, pos)
        log = self.viper_ast.Inhale(pred_acc_pred, pos)
        self.seqn_with_info([log], f"Event: {event.name}", res)

    def _translate_external_call(self,
                                 node: ast.Expr,
                                 to: Expr,
                                 amount: Optional[Expr],
                                 constant: bool,
                                 res: List[Stmt],
                                 ctx: Context,
                                 known: Tuple[VyperInterface, VyperFunction, List[Expr]] = None) -> Tuple[Expr, Expr]:
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
            self.balance_translator.check_balance(amount, res, ctx, pos)
            self.balance_translator.increase_sent(to, amount, res, ctx, pos)

            if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
                resource = self.resource_translator.resource(names.WEI, [], ctx, pos)
                self.allocation_translator.deallocate(node, resource, to, amount, res, ctx, pos)

            self.balance_translator.decrease_balance(amount, res, ctx, pos)

        # In init set the old self state to the current self state, if this is the
        # first public state.
        if ctx.function.name == names.INIT:
            self.state_translator.check_first_public_state(res, ctx, True)

        modelt = self.model_translator.save_variables(res, ctx, pos)

        for check in chain(ctx.function.checks, ctx.program.general_checks):
            check_cond = self.spec_translator.translate_check(check, res, ctx)
            via = [Via('check', check_cond.pos())]
            check_pos = self.to_position(node, ctx, rules.CALL_CHECK_FAIL, via, modelt)
            res.append(self.viper_ast.Assert(check_cond, check_pos))

        for inv in ctx.program.invariants:
            # We ignore accessible because it only has to be checked in the end of
            # the function
            cond = self.spec_translator.translate_invariant(inv, res, ctx, True)
            via = [Via('invariant', cond.pos())]
            call_pos = self.to_position(node, ctx, rules.CALL_INVARIANT_FAIL, via, modelt)
            res.append(self.viper_ast.Assert(cond, call_pos))

        # We check that the invariant tracks all allocation by doing a leak check.
        if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
            self.allocation_translator.send_leak_check(node, res, ctx, pos)

        send_fail_name = ctx.new_local_var_name('send_fail')
        send_fail = self.viper_ast.LocalVarDecl(send_fail_name, self.viper_ast.Bool)
        ctx.new_local_vars.append(send_fail)
        fail_cond = send_fail.localVar()
        call_failed = helpers.call_failed(self.viper_ast, to, pos)
        self.fail_if(fail_cond, [call_failed], res, ctx, pos)

        self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx)

        # We forget about events by exhaling all permissions to the event predicates, i.e.
        # for all event predicates e we do
        #   exhale forall arg0, arg1, ... :: perm(e(arg0, arg1, ...)) > none ==> acc(e(...), perm(e(...)))
        # We use an implication with a '> none' because of a bug in Carbon (TODO: issue #171) where it isn't possible
        # to exhale no permissions under a quantifier.
        for event in ctx.program.events.values():
            event_name = mangled.event_name(event.name)
            types = [self.type_translator.translate(arg, ctx) for arg in event.type.arg_types]
            event_args = [self.viper_ast.LocalVarDecl(f'$arg{idx}', type, pos) for idx, type in enumerate(types)]
            local_args = [arg.localVar() for arg in event_args]
            pa = self.viper_ast.PredicateAccess(local_args, event_name, pos)
            perm = self.viper_ast.CurrentPerm(pa, pos)
            pap = self.viper_ast.PredicateAccessPredicate(pa, perm, pos)
            none = self.viper_ast.NoPerm(pos)
            impl = self.viper_ast.Implies(self.viper_ast.GtCmp(perm, none, pos), pap)
            trigger = self.viper_ast.Trigger([pa], pos)
            forall = self.viper_ast.Forall(event_args, [trigger], impl, pos)
            res.append(self.viper_ast.Exhale(forall, pos))

        if not constant:
            # Save the values of to, amount, and args, as self could be changed by reentrancy
            if known:

                def new_var(var, name='v'):
                    var_name = ctx.new_local_var_name(name)
                    var_decl = self.viper_ast.LocalVarDecl(var_name, var.typ(), pos)
                    ctx.new_local_vars.append(var_decl)
                    res.append(self.viper_ast.LocalVarAssign(var_decl.localVar(), var))
                    return var_decl.localVar()

                to = new_var(to, 'to')
                if amount:
                    amount = new_var(amount, 'amount')
                # Force evaluation at this point
                args = list(map(new_var, args))

            # Havoc state
            self.state_translator.havoc_state(ctx.current_state, res, ctx, pos)

            type_ass = self.type_translator.type_assumptions(self_var, ctx.self_type, ctx)
            assume_type_ass = [self.viper_ast.Inhale(inv) for inv in type_ass]
            self.seqn_with_info(assume_type_ass, "Assume type assumptions", res)

            assume_posts = []
            for post in ctx.program.transitive_postconditions:
                post_expr = self.spec_translator.translate_postcondition(post, assume_posts, ctx)
                ppos = self.to_position(post, ctx, rules.INHALE_POSTCONDITION_FAIL)
                assume_posts.append(self.viper_ast.Inhale(post_expr, ppos))

            self.seqn_with_info(assume_posts, "Assume transitive postconditions", res)

            assume_invs = []
            for inv in ctx.unchecked_invariants():
                assume_invs.append(self.viper_ast.Inhale(inv))

            for inv in ctx.program.invariants:
                cond = self.spec_translator.translate_invariant(inv, assume_invs, ctx, True)
                ipos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                assume_invs.append(self.viper_ast.Inhale(cond, ipos))

            self.seqn_with_info(assume_invs, "Assume invariants", res)

        if node.type:
            ret_name = ctx.new_local_var_name('raw_ret')
            ret_type = self.type_translator.translate(node.type, ctx)
            ret_var = self.viper_ast.LocalVarDecl(ret_name, ret_type, pos)
            ctx.new_local_vars.append(ret_var)
            return_value = ret_var.localVar()
            type_ass = self.type_translator.type_assumptions(return_value, node.type, ctx)
            res.extend(self.viper_ast.Inhale(ass) for ass in type_ass)
        else:
            return_value = None

        success = self.viper_ast.Not(fail_cond, pos)

        if known:
            amount = amount or self.viper_ast.IntLit(0)
            self._assume_interface_specifications(node, interface, function, args, to, amount, success, return_value, res, ctx)

        self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx)

        return success, return_value

    def _assume_interface_specifications(self,
                                         node: ast.Node,
                                         interface: VyperInterface,
                                         function: VyperFunction,
                                         args: List[Expr],
                                         to: Expr,
                                         amount: Expr,
                                         succ: Expr,
                                         return_value: Optional[Expr],
                                         res: List[Stmt],
                                         ctx: Context):
        with ctx.interface_call_scope():
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
                ret_name = ctx.inline_prefix + mangled.RESULT_VAR
                ret_pos = return_value.pos()
                ctx.result_var = TranslatedVar(names.RESULT, ret_name, function.type.return_type, self.viper_ast, ret_pos)
                ctx.new_local_vars.append(ctx.result_var.var_decl(ctx, ret_pos))
                body.append(self.viper_ast.LocalVarAssign(ctx.result_var.local_var(ret_pos), return_value, ret_pos))

            # Add success variable
            succ_name = ctx.inline_prefix + mangled.SUCCESS_VAR
            succ_var = TranslatedVar(names.SUCCESS, succ_name, types.VYPER_BOOL, self.viper_ast, succ.pos())
            ctx.new_local_vars.append(succ_var.var_decl(ctx))
            ctx.success_var = succ_var
            body.append(self.viper_ast.LocalVarAssign(succ_var.local_var(ctx), succ, succ.pos()))

            translate = self.spec_translator.translate_postcondition
            pos = self.to_position(node, ctx, rules.INHALE_INTERFACE_FAIL)

            with ctx.program_scope(interface):
                with ctx.self_address_scope(to):
                    postconditions = chain(function.postconditions, interface.general_postconditions)
                    exprs = [translate(post, body, ctx) for post in postconditions]
                    body.extend(self.viper_ast.Inhale(expr, pos) for expr in exprs)

            if ctx.program.config.has_option(names.CONFIG_TRUST_CASTS):
                res.extend(body)
            else:
                implements = helpers.implements(self.viper_ast, to, interface.name, ctx, pos)
                res.append(self.viper_ast.If(implements, body, [], pos))

    def _translate_var(self, var: VyperVar, ctx: Context) -> TranslatedVar:
        pos = self.to_position(var.node, ctx)
        name = mangled.local_var_name(ctx.inline_prefix, var.name)
        return TranslatedVar(var.name, name, var.type, self.viper_ast, pos)
