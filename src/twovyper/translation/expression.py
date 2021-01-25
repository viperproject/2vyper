"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from functools import reduce
from itertools import chain
from typing import List, Optional, Tuple, Callable


from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.arithmetic import Decimal
from twovyper.ast.nodes import VyperFunction, VyperInterface, VyperVar, VyperEvent, VyperProgram
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
from twovyper.translation.wrapped_viper_ast import WrappedViperAST

from twovyper.utils import switch, first_index

from twovyper.verification import rules
from twovyper.verification.error import Via
from twovyper.verification.model import ModelTransformation

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


# noinspection PyUnusedLocal
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

    def translate_top_level_expression(self, node: ast.Expr, res: List[Stmt], ctx: Context):
        """
        A top level expression is an expression directly used in a statement.

        Generally, we do not need to $wrap inside of a top level expression. Therefore, we only keep the information if
        some expressions got unwrapped inside this expression and if this expression could get wrapped. If both is true,
        only then we wrap this expression again.
        Doing this, prevents the $wrap($unwrap($wrap($unwrap(...))) chain during translation.

        If we are inside an interpreted scope, we do not wrap the result again.
        """
        if isinstance(self.viper_ast, WrappedViperAST) and not ctx.inside_interpreted:
            self.viper_ast.unwrapped_some_expressions = False
            result = self.translate(node, res, ctx)
            if self.viper_ast.unwrapped_some_expressions:
                if types.is_numeric(node.type) and self.arithmetic_translator.is_unwrapped(result):
                    result = helpers.w_wrap(self.viper_ast, result)
            return result
        else:
            return self.translate(node, res, ctx)

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

        if node.id == names.SELF and (node.type == types.VYPER_ADDRESS
                                      or isinstance(node.type, (ContractType, InterfaceType))):
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

        if node.op in self.arithmetic_translator.non_linear_ops:
            # Since we need the information if an expression was wrapped, we can treat this expressions as top-level.
            left = self.translate_top_level_expression(node.left, res, ctx)
            right = self.translate_top_level_expression(node.right, res, ctx)
        else:
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
        expr_list = self.translate(node.list, res, ctx)

        if node.op == ast.ContainmentOperator.IN:
            return helpers.array_contains(self.viper_ast, value, expr_list, pos)
        elif node.op == ast.ContainmentOperator.NOT_IN:
            return helpers.array_not_contains(self.viper_ast, value, expr_list, pos)
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

        viper_type = self.type_translator.translate(node.type, ctx)
        get = helpers.struct_get(self.viper_ast, struct, node.attr, viper_type, struct_type, pos)
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
        else:
            assert False

        return call

    def translate_List(self, node: ast.List, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        if not node.elements:
            viper_type = self.type_translator.translate(node.type.element_type, ctx)
            return self.viper_ast.EmptySeq(viper_type, pos)
        else:
            elems = [self.translate(e, res, ctx) for e in node.elements]
            return self.viper_ast.ExplicitSeq(elems, pos)

    def translate_Str(self, node: ast.Str, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        if not node.s:
            viper_type = self.type_translator.translate(node.type.element_type, ctx)
            return self.viper_ast.EmptySeq(viper_type, pos)
        else:
            elems = [self.viper_ast.IntLit(e, pos) for e in bytes(node.s, 'utf-8')]
            return self.viper_ast.ExplicitSeq(elems, pos)

    def translate_Bytes(self, node: ast.Bytes, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        if not node.s:
            viper_type = self.type_translator.translate(node.type.element_type, ctx)
            return self.viper_ast.EmptySeq(viper_type, pos)
        else:
            elems = [self.viper_ast.IntLit(e, pos) for e in node.s]
            return self.viper_ast.ExplicitSeq(elems, pos)

    def translate_Tuple(self, node: ast.Tuple, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        new_ret = helpers.havoc_var(self.viper_ast, helpers.struct_type(self.viper_ast), ctx)
        for idx, element in enumerate(node.elements):
            viper_type = self.type_translator.translate(element.type, ctx)
            value = self.translate(element, res, ctx)
            new_ret = helpers.struct_set_idx(self.viper_ast, new_ret, value, idx, viper_type, pos)
        return new_ret

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
            else:
                assert False

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
            second_arg = node.args[1]
            assert isinstance(second_arg, ast.Str)
            unit = second_arg.s
            unit_pos = self.to_position(second_arg, ctx)
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

            def concat(arguments):
                argument, *tail = arguments
                if not tail:
                    return argument
                else:
                    return self.viper_ast.SeqAppend(argument, concat(tail), pos)

            return concat(concats)
        elif name == names.EXTRACT32:
            b = self.translate(node.args[0], res, ctx)
            b_len = helpers.array_length(self.viper_ast, b, pos)
            zero = self.viper_ast.IntLit(0, pos)
            start = self.translate(node.args[1], res, ctx)
            lit_32 = self.viper_ast.IntLit(32, pos)
            end = self.viper_ast.Add(lit_32, start, pos)

            # General revert conditions
            start_is_negative = self.viper_ast.LtCmp(start, zero, pos)
            seq_too_small = self.viper_ast.LtCmp(b_len, end, pos)
            cond = self.viper_ast.Or(start_is_negative, seq_too_small)
            self.fail_if(cond, [], res, ctx, pos)

            # Convert byte list to desired type
            b_sliced = self.viper_ast.SeqTake(b, end, pos)
            b_sliced = self.viper_ast.SeqDrop(b_sliced, start, pos)
            b_bytes32 = helpers.pad32(self.viper_ast, b_sliced, pos)

            with switch(node.type) as case:
                if case(types.VYPER_BYTES32):
                    i = b_bytes32
                elif case(types.VYPER_INT128):
                    i = helpers.convert_bytes32_to_signed_int(self.viper_ast, b_bytes32, pos)
                    self.arithmetic_translator.check_under_overflow(i, types.VYPER_INT128, res, ctx, pos)
                elif case(types.VYPER_ADDRESS):
                    i = helpers.convert_bytes32_to_unsigned_int(self.viper_ast, b_bytes32, pos)
                    self.arithmetic_translator.check_under_overflow(i, types.VYPER_ADDRESS, res, ctx, pos)
                else:
                    assert False
            return i
        elif name == names.EMPTY:
            return self.type_translator.default_value(node, node.type, res, ctx)
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
                    return helpers.w_wrap(self.viper_ast, self.viper_ast.CondExp(arg, d_one_lit, zero, pos))
                elif case(types.VYPER_BOOL, types.VYPER_BYTES32):
                    return self.viper_ast.CondExp(arg, one_array, zero_array, pos)
                elif case(types.VYPER_BOOL, _, where=types.is_numeric(to_type)):
                    return helpers.w_wrap(self.viper_ast, self.viper_ast.CondExp(arg, one, zero, pos))
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
            block_number = helpers.struct_get(self.viper_ast, block, names.BLOCK_NUMBER, number_type,
                                              types.BLOCK_TYPE, pos)

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
                self.allocation_translator.deallocate_wei(node, to, balance, res, ctx, pos)

            val = self.viper_ast.TrueLit(pos)
            member = mangled.SELFDESTRUCT_FIELD
            viper_type = self.type_translator.translate(self_type.member_types[member], ctx)
            sset = helpers.struct_set(self.viper_ast, self_var, val, member, viper_type, self_type, pos)
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
            is_static = False
            for kw in node.keywords:
                arg = self.translate(kw.value, res, ctx)
                if kw.name == names.RAW_CALL_VALUE:
                    amount = arg
                elif kw.name == names.RAW_CALL_IS_STATIC_CALL:
                    assert isinstance(kw.value, ast.Bool)
                    is_static = kw.value.value

            _, call = self._translate_external_call(node, to, amount, is_static, res, ctx)
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
                self.log_event(event, args, log_event, ctx, pos)
                res.append(self.viper_ast.If(condition, log_event, [], pos))

            return None
        elif name == names.CREATE_FORWARDER_TO:
            at = self.translate(node.args[0], res, ctx)
            if node.keywords:
                amount = self.translate(node.keywords[0].value, res, ctx)

                if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
                    msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
                    self.allocation_translator.deallocate_wei(node, msg_sender, amount, res, ctx, pos)

                self.balance_translator.check_balance(amount, res, ctx, pos)
                self.balance_translator.increase_sent(at, amount, res, ctx, pos)
                self.balance_translator.decrease_balance(amount, res, ctx, pos)

            new_name = ctx.new_local_var_name('$new')
            viper_type = self.type_translator.translate(node.type, ctx)
            new_var_decl = self.viper_ast.LocalVarDecl(new_name, viper_type, pos)
            ctx.new_local_vars.append(new_var_decl)
            new_var = new_var_decl.localVar()

            eq_zero = self.viper_ast.EqCmp(new_var, self.viper_ast.IntLit(0, pos), pos)
            self.fail_if(eq_zero, [], res, ctx, pos)

            return new_var
        # This is a struct initializer
        elif len(node.args) == 1 and isinstance(node.args[0], ast.Dict):
            first_arg = node.args[0]
            assert isinstance(first_arg, ast.Dict)
            exprs = {}
            for key, value in zip(first_arg.keys, first_arg.values):
                value_expr = self.translate(value, res, ctx)
                idx = node.type.member_indices[key.id]
                exprs[idx] = value_expr

            init_args = [exprs[i] for i in range(len(exprs))]
            init = helpers.struct_init(self.viper_ast, init_args, node.type, pos)
            return init
        # This is a contract / interface initializer
        elif name in ctx.current_program.contracts or name in ctx.current_program.interfaces:
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
                pure = rec_type.function_modifiers[node.name] == names.PURE
                _, call_result = self._translate_external_call(node, to, amount, const or pure, res, ctx)
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
        else:
            assert isinstance(node.receiver, ast.Name)
            if node.receiver.id == names.LOG:
                event = ctx.program.events[name]
                self.log_event(event, args, res, ctx, pos)
                return None
            elif node.receiver.id == names.LEMMA:
                lemma = ctx.program.lemmas[node.name]
                mangled_name = mangled.lemma_name(node.name)
                call_pos = self.to_position(lemma.node, ctx)
                via = Via('lemma', call_pos)
                pos = self.to_position(node, ctx, vias=[via], rules=rules.LEMMA_FAIL, values={'function': lemma})
                args = [self.translate_top_level_expression(arg, res, ctx) for arg in node.args]
                for idx, arg_var in enumerate(lemma.args.values()):
                    if types.is_numeric(arg_var.type):
                        if self.arithmetic_translator.is_unwrapped(args[idx]):
                            args[idx] = helpers.w_wrap(self.viper_ast, args[idx], pos)
                viper_ast = self.viper_ast
                if isinstance(viper_ast, WrappedViperAST):
                    viper_ast = viper_ast.viper_ast
                return viper_ast.FuncApp(mangled_name, args, pos, type=self.viper_ast.Bool)
            else:
                assert False

    def assert_caller_private(self, modelt: ModelTransformation, res: List[Stmt], ctx: Context, vias: List[Via] = None):
        for interface_type in ctx.program.implements:
            interface = ctx.program.interfaces[interface_type.name]
            with ctx.program_scope(interface):
                with ctx.state_scope(ctx.current_state, ctx.current_old_state):
                    for caller_private in interface.caller_private:
                        pos = self.to_position(caller_private, ctx, rules.CALLER_PRIVATE_FAIL, vias or [], modelt)
                        # Quantified variable
                        q_name = mangled.quantifier_var_name(mangled.CALLER)
                        q_var = TranslatedVar(mangled.CALLER, q_name, types.VYPER_ADDRESS, self.viper_ast, pos)
                        ctx.locals[mangled.CALLER] = q_var

                        # $caller != msg.sender ==> Expr == old(Expr)
                        msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
                        ignore_cond = self.viper_ast.NeCmp(msg_sender, q_var.local_var(ctx, pos), pos)
                        _, curr_caller_private = self.spec_translator.translate_caller_private(caller_private, ctx)
                        with ctx.state_scope(ctx.current_old_state, ctx.current_old_state):
                            cond, old_caller_private = self.spec_translator\
                                .translate_caller_private(caller_private, ctx)
                        ignore_cond = self.viper_ast.And(ignore_cond, cond, pos)
                        caller_private_cond = self.viper_ast.EqCmp(curr_caller_private, old_caller_private, pos)
                        expr = self.viper_ast.Implies(ignore_cond, caller_private_cond, pos)

                        # Address type assumption
                        type_assumptions = self.type_translator.type_assumptions(q_var.local_var(ctx), q_var.type, ctx)
                        type_assumptions = reduce(self.viper_ast.And, type_assumptions, self.viper_ast.TrueLit())
                        expr = self.viper_ast.Implies(type_assumptions, expr, pos)

                        # Assertion
                        forall = self.viper_ast.Forall([q_var.var_decl(ctx)], [], expr, pos)
                        res.append(self.viper_ast.Assert(forall, pos))

    def assume_own_resources_stayed_constant(self, res: List[Stmt], ctx: Context, pos=None):
        if not ctx.program.config.has_option(names.CONFIG_ALLOCATION):
            return
        
        interface_names = [t.name for t in ctx.current_program.implements]
        interfaces = [ctx.current_program.interfaces[name] for name in interface_names]
        # The underlying wei resource must be translated differently. Therefore, exclude it for the moment.
        own_resources = [(name, resource) for name, resource in ctx.current_program.own_resources.items()
                         if name != names.UNDERLYING_WEI]
        for i in interfaces:
            interface_resources = [(name, resource) for name, resource in i.own_resources.items()
                                   if name != names.UNDERLYING_WEI]
            own_resources.extend(interface_resources)

        translated_resources1 = self.resource_translator\
            .translate_resources_for_quantified_expr(own_resources, ctx, pos)
        translated_resources2 = self.resource_translator\
            .translate_resources_for_quantified_expr(own_resources, ctx, pos, args_idx_start=len(translated_resources1))

        # Special translation for creator resources
        creator_resource = helpers.creator_resource()
        arg = self.viper_ast.LocalVarDecl(f'$arg$$1', helpers.struct_type(self.viper_ast), pos)
        t_resource = self.resource_translator.creator_resource(arg.localVar(), ctx, pos)
        translated_resources1.append((t_resource, [arg], self.viper_ast.TrueLit()))
        arg = self.viper_ast.LocalVarDecl(f'$arg$$2', helpers.struct_type(self.viper_ast), pos)
        t_resource = self.resource_translator.creator_resource(arg.localVar(), ctx, pos)
        translated_resources2.append((t_resource, [arg], self.viper_ast.TrueLit()))

        # forall({r: own Resources}, allocated[r]() == old(allocated[r]()))
        current_allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx)
        old_allocated = ctx.current_old_state[mangled.ALLOCATED].local_var(ctx)
        for t_resource, args, type_cond in translated_resources1:
            current_allocated_map = self.allocation_translator.get_allocated_map(current_allocated, t_resource, ctx)
            old_allocated_map = self.allocation_translator.get_allocated_map(old_allocated, t_resource, ctx)
            allocated_eq = self.viper_ast.EqCmp(current_allocated_map, old_allocated_map, pos)
            trigger = self.viper_ast.Trigger([current_allocated_map, t_resource], pos)
            forall_eq = self.viper_ast.Forall([*args], [trigger],
                                              self.viper_ast.Implies(type_cond, allocated_eq, pos), pos)
            res.append(self.viper_ast.Inhale(forall_eq, pos))

        # trusted(self) == old(trusted(self))
        current_trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx)
        old_trusted = ctx.current_old_state[mangled.TRUSTED].local_var(ctx)
        self_addr = ctx.self_address or helpers.self_address(self.viper_ast, pos)
        current_trusted_map = self.allocation_translator.get_trusted_map(current_trusted, self_addr, ctx)
        old_trusted_map = self.allocation_translator.get_trusted_map(old_trusted, self_addr, ctx)
        eq = self.viper_ast.EqCmp(current_trusted_map, old_trusted_map, pos)
        res.append(self.viper_ast.Inhale(eq, pos))

        # Quantified address variable
        address = self.viper_ast.LocalVarDecl('$a', self.viper_ast.Int)
        address_var = address.localVar()
        address_type_conds = self.type_translator.type_assumptions(address_var, types.VYPER_ADDRESS, ctx)
        address_type_cond = reduce(lambda l, r: self.viper_ast.And(l, r, pos),
                                   address_type_conds, self.viper_ast.TrueLit())

        # forall({r1: own Resources, r2: own Resources}, offered[r1 <-> r2]() == old(offered[r1 <-> r2]())
        current_offered = ctx.current_state[mangled.OFFERED].local_var(ctx)
        old_offered = ctx.current_old_state[mangled.OFFERED].local_var(ctx)
        for index, (t_resource1, args1, type_cond1) in enumerate(translated_resources1):
            resource1 = own_resources[index][1] if index < len(own_resources) else None
            for t_resource2, args2, type_cond2 in translated_resources2:
                current_offered_map = self.allocation_translator.get_offered_map(current_offered, t_resource1,
                                                                                 t_resource2, ctx)
                old_offered_map = self.allocation_translator.get_offered_map(old_offered, t_resource1, t_resource2, ctx)
                offered_eq = self.viper_ast.EqCmp(current_offered_map, old_offered_map, pos)
                type_cond = self.viper_ast.And(type_cond1, type_cond2)
                forall_eq = self.viper_ast.Forall(
                    [*args1, *args2], [self.viper_ast.Trigger([current_offered_map], pos),
                                       self.viper_ast.Trigger([old_offered_map], pos)],
                    self.viper_ast.Implies(type_cond, offered_eq, pos), pos)
                res.append(self.viper_ast.Inhale(forall_eq, pos))

            if resource1 is not None and resource1.underlying_resource is not None:
                if resource1.name == names.WEI:
                    t_underlying_resource = self.resource_translator.underlying_wei_resource(ctx)
                else:
                    t_underlying_address = self.spec_translator.translate(resource1.underlying_address, res, ctx)
                    args = self.viper_ast.to_list(t_resource1.getArgs())
                    args.pop()
                    args.append(t_underlying_address)
                    assert isinstance(resource1.type, types.DerivedResourceType)
                    t_underlying_resource = helpers.struct_init(self.viper_ast, args,
                                                                resource1.type.underlying_resource)

                current_offered_map = self.allocation_translator.get_offered_map(current_offered, t_resource1,
                                                                                 t_underlying_resource, ctx)
                old_offered_map = self.allocation_translator.get_offered_map(old_offered, t_resource1,
                                                                             t_underlying_resource, ctx)
                offered_eq = self.viper_ast.EqCmp(current_offered_map, old_offered_map, pos)
                forall_eq = self.viper_ast.Forall(
                    [*args1], [self.viper_ast.Trigger([current_offered_map], pos),
                               self.viper_ast.Trigger([old_offered_map], pos)],
                    self.viper_ast.Implies(type_cond1, offered_eq, pos), pos)
                res.append(self.viper_ast.Inhale(forall_eq, pos))

            no_offers = helpers.no_offers(self.viper_ast, old_offered, t_resource1, address_var)
            curr_no_offers = helpers.no_offers(self.viper_ast, current_offered, t_resource1, address_var)
            implies = self.viper_ast.Implies(no_offers, curr_no_offers, pos)
            trigger = self.viper_ast.Trigger([curr_no_offers], pos)
            type_cond = self.viper_ast.And(type_cond1, address_type_cond)
            forall_eq = self.viper_ast.Forall([address, *args1], [trigger],
                                              self.viper_ast.Implies(type_cond, implies))
            res.append(self.viper_ast.Inhale(forall_eq, pos))

    def assume_interface_resources_stayed_constant(self, interface, interface_inst, res, ctx: Context, pos=None):
        if isinstance(interface, VyperProgram):
            with ctx.program_scope(interface):
                with ctx.self_address_scope(interface_inst):
                    self.assume_own_resources_stayed_constant(res, ctx, pos)

    def _implicit_resource_caller_private_expressions(self, interface, self_address, res, ctx, pos=None):
        if not ctx.program.config.has_option(names.CONFIG_ALLOCATION):
            return

        body = []
        # Quantified self address
        q_self_address_from_context = []
        q_self_address_name = mangled.quantifier_var_name(names.INTERFACE)
        q_self_address = ctx.quantified_vars.get(q_self_address_name)
        if q_self_address is not None:
            q_self_address_from_context = [q_self_address.var_decl(ctx)]
        # Interface Address
        interface_addr = ctx.self_address or helpers.self_address(self.viper_ast)
        # Quantified address variable
        address = self.viper_ast.LocalVarDecl('$a', self.viper_ast.Int)
        address_var = address.localVar()
        type_conds = self.type_translator.type_assumptions(address_var, types.VYPER_ADDRESS, ctx)
        type_cond = reduce(lambda l, r: self.viper_ast.And(l, r, pos), type_conds, self.viper_ast.TrueLit())
        # forall({a: address}, trusted(a, by=self, where=interface)
        #   == old(trusted(a, by=self, where=interface)))
        current_trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx)
        old_trusted = ctx.current_old_state[mangled.TRUSTED].local_var(ctx)
        curr_trusted_value = self.allocation_translator.get_trusted(current_trusted, interface_addr,
                                                                    address_var, self_address, ctx)
        old_trusted_value = self.allocation_translator.get_trusted(old_trusted, interface_addr,
                                                                   address_var, self_address, ctx)
        trusted_eq = self.viper_ast.EqCmp(curr_trusted_value, old_trusted_value)
        forall_eq = self.viper_ast.Forall([address, *q_self_address_from_context],
                                          [self.viper_ast.Trigger([old_trusted_value], pos),
                                           self.viper_ast.Trigger([curr_trusted_value], pos)],
                                          self.viper_ast.Implies(type_cond, trusted_eq))
        body.append(self.viper_ast.Inhale(forall_eq, pos))

        current_trust_no_one = helpers.trust_no_one(self.viper_ast, current_trusted, self_address, interface_addr)
        old_trust_no_one = helpers.trust_no_one(self.viper_ast, old_trusted, self_address, interface_addr)
        forall_implies = self.viper_ast.Forall([*q_self_address_from_context],
                                               [self.viper_ast.Trigger([current_trust_no_one], pos),
                                                self.viper_ast.Trigger([old_trust_no_one], pos)],
                                               self.viper_ast.Implies(old_trust_no_one, current_trust_no_one))
        body.append(self.viper_ast.Inhale(forall_implies, pos))

        # Declared resources of interface
        resources = interface.declared_resources.items()
        translated_resources1 = self.resource_translator.translate_resources_for_quantified_expr(resources, ctx)
        translated_resources2 = self.resource_translator\
            .translate_resources_for_quantified_expr(resources, ctx, args_idx_start=len(translated_resources1))
        # No trust condition
        trust_no_one = helpers.trust_no_one(self.viper_ast, old_trusted,
                                            self_address, interface_addr)
        # Quantified offer struct variable
        offer = self.viper_ast.LocalVarDecl('$o', helpers.struct_type(self.viper_ast))
        offer_var = offer.localVar()
        # Offered map type
        offered_type = helpers.offered_type()
        k_type = self.type_translator.translate(offered_type.value_type.value_type.key_type, ctx)
        v_type = self.type_translator.translate(offered_type.value_type.value_type.value_type, ctx)
        # forall({r1: Resource on interface, r2: Resource on interface, o: Offer},
        #   trust_no_one(self, interface) ==> old(offered[r1 <-> r2][o]) == 0 ==>
        #   offered[r1 <-> r2][o] == 0)
        current_offered = ctx.current_state[mangled.OFFERED].local_var(ctx)
        old_offered = ctx.current_old_state[mangled.OFFERED].local_var(ctx)
        for t_resource1, args1, type_cond1 in translated_resources1:
            for t_resource2, args2, type_cond2 in translated_resources2:
                current_offered_map = self.allocation_translator \
                    .get_offered_map(current_offered, t_resource1, t_resource2, ctx)
                old_offered_map = self.allocation_translator \
                    .get_offered_map(old_offered, t_resource1, t_resource2, ctx)

                current_offered_map_get = helpers.map_get(self.viper_ast, current_offered_map,
                                                          offer_var, k_type, v_type)
                old_offered_map_get = helpers.map_get(self.viper_ast, old_offered_map,
                                                      offer_var, k_type, v_type)

                offered_eq = self.viper_ast.EqCmp(current_offered_map_get, old_offered_map_get)
                type_cond = self.viper_ast.And(type_cond1, type_cond2)
                cond = self.viper_ast.And(trust_no_one, type_cond)
                forall_eq = self.viper_ast.Forall([offer, *args1, *args2, *q_self_address_from_context],
                                                  [self.viper_ast.Trigger([current_offered_map_get], pos),
                                                   self.viper_ast.Trigger([old_offered_map_get], pos)],
                                                  self.viper_ast.Implies(cond, offered_eq))
                body.append(self.viper_ast.Inhale(forall_eq, pos))
        # forall({r: Resource on interface}, trust_no_one(self, interface)
        #   and no_offers[r](self) ==> allocated[r](self) >= old(allocated[r](self)))
        current_allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx)
        old_allocated = ctx.current_old_state[mangled.ALLOCATED].local_var(ctx)
        for t_resource, args, type_cond in translated_resources1:
            # No offers condition
            no_offers = helpers.no_offers(self.viper_ast, old_offered, t_resource, self_address)
            curr_no_offers = helpers.no_offers(self.viper_ast, current_offered, t_resource, self_address)

            current_allocated_map = self.allocation_translator \
                .get_allocated(current_allocated, t_resource, self_address, ctx)
            old_allocated_map = self.allocation_translator \
                .get_allocated(old_allocated, t_resource, self_address, ctx)
            allocated_geq = self.viper_ast.GeCmp(current_allocated_map, old_allocated_map, pos)
            cond = self.viper_ast.And(trust_no_one, no_offers)
            allocated_geq = self.viper_ast.Implies(cond, allocated_geq)
            forall_implies = self.viper_ast.Forall([*args, *q_self_address_from_context],
                                                   [self.viper_ast.Trigger([current_allocated_map], pos),
                                                    self.viper_ast.Trigger([old_allocated_map], pos)],
                                                   self.viper_ast.Implies(type_cond, allocated_geq, pos), pos)
            body.append(self.viper_ast.Inhale(forall_implies, pos))

            forall_implies = self.viper_ast.Forall([*args, *q_self_address_from_context],
                                                   [self.viper_ast.Trigger([no_offers], pos),
                                                    self.viper_ast.Trigger([curr_no_offers], pos)],
                                                   self.viper_ast.Implies(no_offers, curr_no_offers, pos), pos)
            body.append(self.viper_ast.Inhale(forall_implies, pos))

        self.seqn_with_info(body, f"Implicit caller private expr of resources in interface {interface.name}", res)

    def implicit_resource_caller_private_expressions(self, interface, interface_inst, self_address,
                                                     res, ctx: Context, pos=None):
        if isinstance(interface, VyperInterface):
            with ctx.program_scope(interface):
                with ctx.self_address_scope(interface_inst):
                    self._implicit_resource_caller_private_expressions(interface, self_address, res, ctx, pos)

    def assume_contract_state(self, known_interface_refs: List[Tuple[str, Expr]], res: List[Stmt], ctx: Context,
                              receiver: Optional[Expr] = None, skip_caller_private=False):
        for interface_name, interface_ref in known_interface_refs:
            body = []
            if not skip_caller_private:
                # Assume caller private
                interface = ctx.program.interfaces[interface_name]
                with ctx.program_scope(interface):
                    with ctx.state_scope(ctx.current_state, ctx.current_old_state):
                        # Caller variable
                        mangled_name = ctx.new_local_var_name(mangled.CALLER)
                        caller_var = TranslatedVar(mangled.CALLER, mangled_name, types.VYPER_ADDRESS,
                                                   self.viper_ast)
                        ctx.locals[mangled.CALLER] = caller_var
                        ctx.new_local_vars.append(caller_var.var_decl(ctx))
                        self_address = ctx.self_address or helpers.self_address(self.viper_ast)
                        if self.arithmetic_translator.is_wrapped(self_address):
                            self_address = helpers.w_unwrap(self.viper_ast, self_address)
                        assign = self.viper_ast.LocalVarAssign(caller_var.local_var(ctx), self_address)
                        body.append(assign)

                        with ctx.self_address_scope(interface_ref):
                            for caller_private in interface.caller_private:
                                pos = self.to_position(caller_private, ctx, rules.INHALE_CALLER_PRIVATE_FAIL)
                                # Caller private assumption
                                _, curr_caller_private = self.spec_translator\
                                    .translate_caller_private(caller_private, ctx)
                                with ctx.state_scope(ctx.current_old_state, ctx.current_old_state):
                                    cond, old_caller_private = self.spec_translator\
                                        .translate_caller_private(caller_private, ctx)
                                caller_private_cond = self.viper_ast.EqCmp(curr_caller_private, old_caller_private, pos)
                                caller_private_cond = self.viper_ast.Implies(cond, caller_private_cond, pos)
                                body.append(self.viper_ast.Inhale(caller_private_cond, pos))

                            self._implicit_resource_caller_private_expressions(interface, caller_var.local_var(ctx),
                                                                               body, ctx)

            if receiver and body:
                neq_cmp = self.viper_ast.NeCmp(receiver, interface_ref)
                body = helpers.flattened_conditional(self.viper_ast, neq_cmp, body, [])

            # Assume interface invariants
            interface = ctx.program.interfaces[interface_name]
            with ctx.program_scope(interface):
                with ctx.self_address_scope(interface_ref):
                    for inv in ctx.current_program.invariants:
                        cond = self.spec_translator.translate_invariant(inv, res, ctx, True)
                        i_pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        body.append(self.viper_ast.Inhale(cond, i_pos))

            if ctx.program.config.has_option(names.CONFIG_TRUST_CASTS):
                res.extend(body)
            else:
                implements = helpers.implements(self.viper_ast, interface_ref, interface_name, ctx)
                res.extend(helpers.flattened_conditional(self.viper_ast, implements, body, []))

    def log_event(self, event: VyperEvent, args: List[Expr], res: List[Stmt], ctx: Context, pos=None):
        assert ctx
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
        #    - Assert checks, own 'caller private' and inter contract invariants
        #    - The next step is only necessary if the function is modifying:
        #       - Create new old-contract state
        #       - Havoc contract state
        #    - Assert local state invariants
        #    - Fail based on an unknown value (i.e. the call could fail)
        #    - The next step is only necessary if the function is modifying:
        #       - Undo havocing of contract state
        #    - The next steps are only necessary if the function is modifying:
        #       - Create new old state which old in the invariants after the call refers to
        #       - Store state before call (To be used to restore old contract state)
        #       - Havoc state
        #       - Assume 'caller private' of interface state variables but NOT receiver
        #       - Assume invariants of interface state variables and receiver
        #       - Create new old-contract state
        #       - Havoc contract state
        #       - Assume type assumptions for self
        #       - Assume local state invariants (where old refers to the state before send)
        #       - Assume invariants of interface state variables and receiver
        #       - Assume transitive postcondition
        #       - Assume that there were no reentrant calls based on an unknown value
        #       - If there were no reentrant calls:
        #           - Restore state from old state
        #           - Restore old contract state
        #       - Create new old-contract state
        #       - Havoc contract state
        #       - Assume 'caller private' of interface state variables and receiver
        #       - Assert inter contract invariants (during call)
        #       - Create new old-contract state
        #       - Havoc contract state
        #       - Assume 'caller private' of interface state variables but NOT receiver
        #       - Assume invariants of interface state variables and receiver
        #       - Restore old contract state
        #    - In the case of an interface call:
        #       - Assume postconditions
        #    - The next step is only necessary if the function is modifying:
        #       - Assert inter contract invariants (after call)
        #    - Create new old state which subsequent old expressions refer to

        pos = self.to_position(node, ctx)
        self_var = ctx.self_var.local_var(ctx)

        modifying = not constant

        if known:
            interface, function, args = known
        else:
            interface = None
            function = None
            args = None

        if amount:
            self.balance_translator.check_balance(amount, res, ctx, pos)
            self.balance_translator.increase_sent(to, amount, res, ctx, pos)

            if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
                self.allocation_translator.deallocate_wei(node, to, amount, res, ctx, pos)

            self.balance_translator.decrease_balance(amount, res, ctx, pos)

        general_stmts_for_performs = []
        performs_as_stmts_generators = []
        with ctx.inline_scope(None):
            # Create pre_state for function call
            def inlined_pre_state(name: str) -> str:
                return ctx.inline_prefix + mangled.pre_state_var_name(name)
            state_for_performs = self.state_translator.state(inlined_pre_state, ctx)

        if modifying:
            # Save the values of to, amount, and args, as self could be changed by reentrancy
            if known:
                def new_var(variable, name='v'):
                    name += '$'
                    var_name = ctx.new_local_var_name(name)
                    var_decl = self.viper_ast.LocalVarDecl(var_name, variable.typ(), pos)
                    ctx.new_local_vars.append(var_decl)
                    res.append(self.viper_ast.LocalVarAssign(var_decl.localVar(), variable))
                    return var_decl.localVar()

                to = new_var(to, 'to')
                if amount:
                    amount = new_var(amount, 'amount')
                # Force evaluation at this point
                args = list(map(new_var, args))

            if known and function.performs:

                self.state_translator.copy_state(ctx.current_state, state_for_performs, general_stmts_for_performs, ctx)

                performs_as_stmts = {}
                performs_decider_variables = {}
                sender_is_resource_address_map = {}
                with ctx.program_scope(interface):
                    with ctx.self_address_scope(to):
                        with ctx.state_scope(ctx.current_state, ctx.current_old_state):
                            ctx.current_state[mangled.SELF] = state_for_performs[mangled.SELF]
                            ctx.current_state[mangled.CONTRACTS] = state_for_performs[mangled.CONTRACTS]
                            with ctx.interface_call_scope():
                                # Define new msg variable
                                msg_name = ctx.inline_prefix + mangled.MSG
                                msg_var = TranslatedVar(names.MSG, msg_name, types.MSG_TYPE, self.viper_ast)
                                ctx.locals[names.MSG] = msg_var
                                ctx.new_local_vars.append(msg_var.var_decl(ctx))

                                # Assume msg.sender == self and msg.value == amount
                                msg = msg_var.local_var(ctx)
                                svytype = types.MSG_TYPE.member_types[names.MSG_SENDER]
                                svitype = self.type_translator.translate(svytype, ctx)
                                msg_sender = helpers.struct_get(self.viper_ast, msg, names.MSG_SENDER,
                                                                svitype, types.MSG_TYPE)
                                self_address = helpers.self_address(self.viper_ast)
                                general_stmts_for_performs.append(self.viper_ast.Inhale(
                                    self.viper_ast.EqCmp(msg_sender, self_address)))

                                if amount:
                                    vvytype = types.MSG_TYPE.member_types[names.MSG_VALUE]
                                    vvitype = self.type_translator.translate(vvytype, ctx)
                                    msg_value = helpers.struct_get(self.viper_ast, msg, names.MSG_VALUE,
                                                                   vvitype, types.MSG_TYPE)
                                    general_stmts_for_performs.append(self.viper_ast.Inhale(
                                        self.viper_ast.EqCmp(msg_value, amount)))

                                # Arguments as translated variables
                                args_as_translated_var = [
                                    TranslatedVar(name, val.name(), arg.type, self.viper_ast,
                                                  is_local=not self.arithmetic_translator.is_wrapped(val))
                                    for (name, arg), val in zip(function.args.items(), args)]
                                ctx.locals.update((var.name, var) for var in args_as_translated_var)

                                # Assume performs clauses
                                with ctx.derived_resource_performs_scope():
                                    for performs in function.performs:
                                        self.spec_translator.translate_ghost_statement(
                                            performs, general_stmts_for_performs, ctx, is_performs=True)

                                zero = self.viper_ast.IntLit(0)
                                two = self.viper_ast.IntLit(2)

                                for performs_idx, performs in enumerate(function.performs):

                                    location_address = self.allocation_translator.location_address_of_performs(
                                        performs, res, ctx)
                                    if location_address is not None:
                                        sender_is_resource_address = self.viper_ast.EqCmp(msg_sender, location_address)
                                    else:
                                        sender_is_resource_address = self.viper_ast.FalseLit()

                                    perform_as_stmts = []
                                    self.spec_translator.translate(performs, perform_as_stmts, ctx)

                                    performs_var_name = ctx.new_local_var_name("performs_decider_var")
                                    performs_var = TranslatedVar(performs_var_name, performs_var_name,
                                                                 types.VYPER_UINT256, self.viper_ast)
                                    ctx.locals[performs_var_name] = performs_var
                                    ctx.new_local_vars.append(performs_var.var_decl(ctx))

                                    performs_local_var = performs_var.local_var(ctx)
                                    performs_var_ge_zero = self.viper_ast.GeCmp(performs_local_var, zero)
                                    performs_var_le_two = self.viper_ast.LeCmp(performs_local_var, two)
                                    cond = self.viper_ast.And(performs_var_ge_zero, performs_var_le_two)
                                    general_stmts_for_performs.append(self.viper_ast.Inhale(cond))

                                    performs_as_stmts[performs_idx] = perform_as_stmts
                                    performs_decider_variables[performs_idx] = performs_local_var
                                    sender_is_resource_address_map[performs_idx] = sender_is_resource_address

                                    def conditional_perform_generator(p_idx: int) -> Callable[[int], List[Stmt]]:
                                        def conditional_perform(index: int) -> List[Stmt]:
                                            if index >= 0:
                                                idx = self.viper_ast.IntLit(index)
                                                decider_eq_idx = self.viper_ast.EqCmp(
                                                    performs_decider_variables[p_idx], idx)
                                                cond_for_perform = self.viper_ast.And(
                                                    decider_eq_idx, self.viper_ast.Not(
                                                        sender_is_resource_address_map[performs_idx]))
                                                return helpers.flattened_conditional(self.viper_ast, cond_for_perform,
                                                                                     performs_as_stmts[p_idx], [])
                                            else:
                                                return helpers.flattened_conditional(
                                                    self.viper_ast, sender_is_resource_address_map[performs_idx],
                                                    performs_as_stmts[p_idx], [])

                                        return conditional_perform

                                    performs_as_stmts_generators.append(conditional_perform_generator(performs_idx))

            res.extend(general_stmts_for_performs)

        # In init set the old self state to the current self state, if this is the
        # first public state.
        if ctx.function.name == names.INIT:
            self.state_translator.check_first_public_state(res, ctx, True)

        modelt = self.model_translator.save_variables(res, ctx, pos)

        self.assert_caller_private(modelt, res, ctx, [Via('external function call', pos)])
        for check in chain(ctx.function.checks, ctx.program.general_checks):
            check_cond = self.spec_translator.translate_check(check, res, ctx)
            via = [Via('check', check_cond.pos())]
            check_pos = self.to_position(node, ctx, rules.CALL_CHECK_FAIL, via, modelt)
            res.append(self.viper_ast.Assert(check_cond, check_pos))

        def assert_invariants(inv_getter: Callable[[Context], List[ast.Expr]], rule: rules.Rule) -> List[Stmt]:
            res_list = []
            # Assert implemented interface invariants
            for implemented_interface in ctx.program.implements:
                vyper_interface = ctx.program.interfaces[implemented_interface.name]
                with ctx.program_scope(vyper_interface):
                    for inv in inv_getter(ctx):
                        translated_inv = self.spec_translator.translate_invariant(inv, res_list, ctx, True)
                        call_pos = self.to_position(node, ctx, rule, [Via('invariant', translated_inv.pos())], modelt)
                        res_list.append(self.viper_ast.Assert(translated_inv, call_pos))

            # Assert own invariants
            for inv in inv_getter(ctx):
                # We ignore accessible because it only has to be checked in the end of
                # the function
                translated_inv = self.spec_translator.translate_invariant(inv, res_list, ctx, True)
                call_pos = self.to_position(node, ctx, rule, [Via('invariant', translated_inv.pos())], modelt)
                res_list.append(self.viper_ast.Assert(translated_inv, call_pos))
            return res_list

        def assume_invariants(inv_getter: Callable[[Context], List[ast.Expr]]) -> List[Stmt]:
            res_list = []
            # Assume implemented interface invariants
            for implemented_interface in ctx.program.implements:
                vyper_interface = ctx.program.interfaces[implemented_interface.name]
                with ctx.program_scope(vyper_interface):
                    for inv in inv_getter(ctx):
                        translated_inv = self.spec_translator.translate_invariant(inv, res_list, ctx, True)
                        inv_pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        res_list.append(self.viper_ast.Inhale(translated_inv, inv_pos))

            # Assume own invariants
            for inv in inv_getter(ctx):
                translated_inv = self.spec_translator.translate_invariant(inv, res_list, ctx, True)
                inv_pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                res_list.append(self.viper_ast.Inhale(translated_inv, inv_pos))
            return res_list

        assert_inter_contract_invariants = assert_invariants(lambda c: c.current_program.inter_contract_invariants,
                                                             rules.CALL_INVARIANT_FAIL)
        self.seqn_with_info(assert_inter_contract_invariants, "Assert inter contract invariants before call", res)
        assert_derived_resource_invariants = [self.viper_ast.Assert(expr, expr.pos())
                                              for expr in ctx.derived_resources_invariants(node)]
        self.seqn_with_info(assert_derived_resource_invariants, "Assert derived resource invariants before call", res)

        self.forget_about_all_events(res, ctx, pos)

        if modifying:
            # Copy contract state
            self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx,
                                             unless=lambda n: n == mangled.SELF)
            # Havoc contract state
            self.state_translator.havoc_state(ctx.current_state, res, ctx,
                                              unless=lambda n: n == mangled.SELF)
            self.assume_own_resources_stayed_constant(res, ctx, pos)

        assert_local_state_invariants = assert_invariants(lambda c: c.current_program.local_state_invariants,
                                                          rules.CALL_INVARIANT_FAIL)
        self.seqn_with_info(assert_local_state_invariants, "Assert local state invariants before call", res)

        # We check that the invariant tracks all allocation by doing a leak check.
        if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
            self.allocation_translator.send_leak_check(node, res, ctx, pos)

        send_fail_name = ctx.new_local_var_name('send_fail')
        send_fail = self.viper_ast.LocalVarDecl(send_fail_name, self.viper_ast.Bool)
        ctx.new_local_vars.append(send_fail)
        fail_cond = send_fail.localVar()

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

        call_failed = helpers.call_failed(self.viper_ast, to, pos)
        self.fail_if(fail_cond, [call_failed], res, ctx, pos)
        if isinstance(node, ast.ReceiverCall):
            # If it is a receiver call and the receiver is null the transaction will revert.
            self.fail_if(self.viper_ast.EqCmp(to, self.viper_ast.IntLit(0, pos), pos), [call_failed], res, ctx, pos)

        with ctx.inline_scope(None):
            # Create pre_state for function call
            def inlined_pre_state(name: str) -> str:
                return ctx.inline_prefix + mangled.pre_state_var_name(name)
            old_state_for_postconditions = self.state_translator.state(inlined_pre_state, ctx)

        with ctx.inline_scope(None):
            # Create needed states to verify inter contract invariants
            def inlined_pre_state(name: str) -> str:
                return ctx.inline_prefix + mangled.pre_state_var_name(name)
            old_state_for_inter_contract_invariant_during = self.state_translator.state(inlined_pre_state, ctx)

            def inlined_old_state(name: str) -> str:
                return ctx.inline_prefix + mangled.old_state_var_name(name)
            curr_state_for_inter_contract_invariant_during = self.state_translator.state(inlined_old_state, ctx)

        with ctx.inline_scope(None):
            # Create needed states to verify inter contract invariants
            def inlined_pre_state(name: str) -> str:
                return ctx.inline_prefix + mangled.pre_state_var_name(name)
            old_state_for_inter_contract_invariant_after = self.state_translator.state(inlined_pre_state, ctx)

            def inlined_old_state(name: str) -> str:
                return ctx.inline_prefix + mangled.old_state_var_name(name)
            curr_state_for_inter_contract_invariant_after = self.state_translator.state(inlined_old_state, ctx)
        known_interface_ref = []
        if modifying:
            # Collect known interface references
            self_type = ctx.program.fields.type
            for member_name, member_type in self_type.member_types.items():
                viper_type = self.type_translator.translate(member_type, ctx)
                if isinstance(member_type, types.InterfaceType):
                    get = helpers.struct_get(self.viper_ast, ctx.self_var.local_var(ctx), member_name,
                                             viper_type, self_type)
                    known_interface_ref.append((member_type.name, get))

            for var in chain(ctx.locals.values(), ctx.args.values()):
                assert isinstance(var, TranslatedVar)
                if isinstance(var.type, types.InterfaceType):
                    known_interface_ref.append((var.type.name, var.local_var(ctx)))

            # Undo havocing of contract state
            self.state_translator.copy_state(ctx.current_old_state, ctx.current_state, res, ctx,
                                             unless=lambda n: n == mangled.SELF)
            for val in chain(state_for_performs.values(),
                             old_state_for_postconditions.values(),
                             old_state_for_inter_contract_invariant_during.values(),
                             curr_state_for_inter_contract_invariant_during.values(),
                             old_state_for_inter_contract_invariant_after.values(),
                             curr_state_for_inter_contract_invariant_after.values()):
                ctx.new_local_vars.append(val.var_decl(ctx, pos))
        # Copy state
        self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx)
        if modifying:
            # Prepare old state for the postconditions of the external call
            self.state_translator.copy_state(ctx.current_state, old_state_for_postconditions, res, ctx)
            # Havoc state
            self.state_translator.havoc_state(ctx.current_state, res, ctx,
                                              unless=lambda n: n == mangled.SELF)
            self.assume_own_resources_stayed_constant(res, ctx, pos)

            # Prepare old state for inter contract invariants
            assume_caller_private_without_receiver = []
            self.assume_contract_state(known_interface_ref, assume_caller_private_without_receiver, ctx, to)
            self.seqn_with_info(assume_caller_private_without_receiver, "Assume caller private for old state", res)

            caller_address = ctx.self_address or helpers.self_address(self.viper_ast)
            self.implicit_resource_caller_private_expressions(interface, to, caller_address, res, ctx)
            res.extend(stmt for performs_as_stmts in performs_as_stmts_generators for stmt in performs_as_stmts(0))
            self.state_translator.copy_state(ctx.current_state, old_state_for_inter_contract_invariant_during, res, ctx)

            # Assume caller private and create new contract state
            self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx,
                                             unless=lambda n: n == mangled.SELF)
            self.state_translator.havoc_state(ctx.current_state, res, ctx,
                                              unless=lambda n: n == mangled.SELF)
            self.assume_own_resources_stayed_constant(res, ctx, pos)
            self.seqn_with_info(assume_caller_private_without_receiver, "Assume caller private", res)
            self.implicit_resource_caller_private_expressions(interface, to, caller_address, res, ctx)
            res.extend(stmt for performs_as_stmts in performs_as_stmts_generators for stmt in performs_as_stmts(1))
            self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx,
                                             unless=lambda n: n == mangled.SELF)
            self.state_translator.havoc_state(ctx.current_state, res, ctx)

            ############################################################################################################
            #                         We did not yet make any assumptions about the self state.                        #
            #                                                                                                          #
            #  The contract state (which models all self states of other contracts) is at a point where anything could #
            #  have happened, but it is before the receiver of the external call has made any re-entrant call to self. #
            ############################################################################################################

            res.extend(stmt for performs_as_stmts in performs_as_stmts_generators for stmt in performs_as_stmts(-1))
            type_ass = self.type_translator.type_assumptions(self_var, ctx.self_type, ctx)
            assume_type_ass = [self.viper_ast.Inhale(inv) for inv in type_ass]
            self.seqn_with_info(assume_type_ass, "Assume type assumptions", res)

            assume_invs = []
            for inv in ctx.unchecked_invariants():
                assume_invs.append(self.viper_ast.Inhale(inv))
            assume_invs.extend(assume_invariants(lambda c: c.current_program.local_state_invariants))
            self.seqn_with_info(assume_invs, "Assume local state invariants", res)

            # Assume transitive postconditions
            assume_transitive_posts = []
            self.assume_contract_state(known_interface_ref, assume_transitive_posts, ctx, skip_caller_private=True)
            for post in ctx.unchecked_transitive_postconditions():
                assume_transitive_posts.append(self.viper_ast.Inhale(post))
            for post in ctx.program.transitive_postconditions:
                post_expr = self.spec_translator.translate_pre_or_postcondition(post, assume_transitive_posts, ctx)
                ppos = self.to_position(post, ctx, rules.INHALE_POSTCONDITION_FAIL)
                assume_transitive_posts.append(self.viper_ast.Inhale(post_expr, ppos))
            self.seqn_with_info(assume_transitive_posts, "Assume transitive postconditions", res)

            no_reentrant_name = ctx.new_local_var_name('no_reentrant_call')
            no_reentrant = self.viper_ast.LocalVarDecl(no_reentrant_name, self.viper_ast.Bool)
            ctx.new_local_vars.append(no_reentrant)
            no_reentrant_cond = no_reentrant.localVar()
            
            # If there were no reentrant calls, reset the contract state.
            use_zero_reentrant_call_state = []
            self.state_translator.copy_state(ctx.current_old_state, ctx.current_state,
                                             use_zero_reentrant_call_state, ctx)
            res.extend(helpers.flattened_conditional(self.viper_ast, no_reentrant_cond,
                                                     use_zero_reentrant_call_state, []))

            ############################################################################################################
            #      At this point, we have a self state with all the assumptions of a self state in a public state.     #
            #     This self state corresponds to the last state of self after any (zero or more) re-entrant calls.     #
            #                                                                                                          #
            #   The contract state is at this point also at the public state after the last re-entrant call to self.   #
            #   Due to re-entrant calls, any caller private expression might have gotten modified. But we can assume   #
            #              that they are only modified by self and only in such a way as described in the              #
            #                                        transitive postconditions.                                        #
            ############################################################################################################

            # Assume caller private in a new contract state
            self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx,
                                             unless=lambda n: n == mangled.SELF)
            self.state_translator.havoc_state(ctx.current_state, res, ctx,
                                              unless=lambda n: n == mangled.SELF)
            self.assume_own_resources_stayed_constant(res, ctx, pos)
            assume_caller_private = []
            self.assume_contract_state(known_interface_ref, assume_caller_private, ctx)
            self.seqn_with_info(assume_caller_private, "Assume caller private", res)

            ############################################################################################################
            #           Since no more re-entrant calls can happen, the self state does not change anymore.             #
            #                                                                                                          #
            # The contract state is at a point where the last call, which lead to a re-entrant call to self, returned. #
            #   We can assume all caller private expressions of self stayed constant, since the contract state above.  #
            #     We can only assume that variables captured with a caller private expression did not change, since    #
            #   any other contract might got called which could change everything except caller private expressions.   #
            ############################################################################################################

            # Store the states to assert the inter contract invariants during the call
            self.state_translator.copy_state(ctx.current_state, curr_state_for_inter_contract_invariant_during,
                                             res, ctx)
            # Assume caller private in a new contract state
            self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx,
                                             unless=lambda n: n == mangled.SELF)
            self.state_translator.havoc_state(ctx.current_state, res, ctx,
                                              unless=lambda n: n == mangled.SELF)
            self.assume_own_resources_stayed_constant(res, ctx, pos)
            self.seqn_with_info(assume_caller_private_without_receiver, "Assume caller private", res)
            self.implicit_resource_caller_private_expressions(interface, to, caller_address, res, ctx)
            res.extend(stmt for performs_as_stmts in performs_as_stmts_generators for stmt in performs_as_stmts(2))

            ############################################################################################################
            # The contract state is at the point where the external call returns. Since the last modeled public state, #
            #             any non-caller-private expression might have changed but also the caller private             #
            #   expressions of the receiver. Therefore, we can only assume that all but the receiver's caller private  #
            #                                       expressions stayed constant.                                       #
            ############################################################################################################

            # Store the states to assert the inter contract invariants after the call
            self.state_translator.copy_state(ctx.current_state, curr_state_for_inter_contract_invariant_after, res, ctx)
            self.state_translator.copy_state(ctx.current_old_state, old_state_for_inter_contract_invariant_after,
                                             res, ctx)

            # Assume caller private in a new contract state
            self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx,
                                             unless=lambda n: n == mangled.SELF)
            self.state_translator.havoc_state(ctx.current_state, res, ctx,
                                              unless=lambda n: n == mangled.SELF)
            self.assume_own_resources_stayed_constant(res, ctx, pos)
            self.seqn_with_info(assume_caller_private_without_receiver, "Assume caller private", res)
            self.implicit_resource_caller_private_expressions(interface, to, caller_address, res, ctx)

            ############################################################################################################
            #  The contract is at the end of the external call, only changes to the caller private expressions of the  #
            #                            receiver of the external call could have happened.                            #
            #  This state models the same state as the previous. But, we must not assert the inter contract invariants #
            #                             in the state where we assumed the postcondition.                             #
            ############################################################################################################

            # Restore old state for postcondition
            self.state_translator.copy_state(old_state_for_postconditions, ctx.current_old_state, res,
                                             ctx, unless=lambda n: n == mangled.SELF)

            # Assume type assumptions for allocation maps
            self.state_translator.assume_type_assumptions_for_state(
                {name: state for name, state in ctx.current_state.items() if StateTranslator.is_allocation(name)},
                "State after call", res, ctx)

        success = self.viper_ast.Not(fail_cond, pos)
        amount = amount or self.viper_ast.IntLit(0)
        # Assume postcondition of the external call
        if known:
            self._assume_interface_specifications(node, interface, function, args, to, amount, success,
                                                  return_value, res, ctx)

        if modifying:
            # Assert inter contract invariants during call
            with ctx.state_scope(curr_state_for_inter_contract_invariant_during,
                                 old_state_for_inter_contract_invariant_during):
                assert_invs = assert_invariants(lambda c: c.current_program.inter_contract_invariants,
                                                rules.DURING_CALL_INVARIANT_FAIL)
            self.seqn_with_info(assert_invs, "Assert inter contract invariants during call", res)
            # Assert inter contract invariants after call
            with ctx.state_scope(curr_state_for_inter_contract_invariant_after,
                                 old_state_for_inter_contract_invariant_after):
                assert_invs = assert_invariants(lambda c: c.current_program.inter_contract_invariants,
                                                rules.DURING_CALL_INVARIANT_FAIL)
            self.seqn_with_info(assert_invs, "Assert inter contract invariants after call", res)

        self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, res, ctx)

        return success, return_value

    def forget_about_all_events(self, res, ctx, pos):
        # We forget about events by exhaling all permissions to the event predicates, i.e.
        # for all event predicates e we do
        #   exhale forall arg0, arg1, ... :: perm(e(arg0, arg1, ...)) > none ==> acc(e(...), perm(e(...)))
        # We use an implication with a '> none' because of a bug in Carbon (TODO: issue #171) where it isn't possible
        # to exhale no permissions under a quantifier.
        for event in ctx.program.events.values():
            event_name = mangled.event_name(event.name)
            viper_types = [self.type_translator.translate(arg, ctx) for arg in event.type.arg_types]
            event_args = [self.viper_ast.LocalVarDecl(f'$arg{idx}', viper_type, pos)
                          for idx, viper_type in enumerate(viper_types)]
            local_args = [arg.localVar() for arg in event_args]
            pa = self.viper_ast.PredicateAccess(local_args, event_name, pos)
            perm = self.viper_ast.CurrentPerm(pa, pos)
            pap = self.viper_ast.PredicateAccessPredicate(pa, perm, pos)
            none = self.viper_ast.NoPerm(pos)
            impl = self.viper_ast.Implies(self.viper_ast.GtCmp(perm, none, pos), pap)
            trigger = self.viper_ast.Trigger([pa], pos)
            forall = self.viper_ast.Forall(event_args, [trigger], impl, pos)
            res.append(self.viper_ast.Exhale(forall, pos))

    def log_all_events_zero_or_more_times(self, res, ctx, pos):
        for event in ctx.program.events.values():
            event_name = mangled.event_name(event.name)
            viper_types = [self.type_translator.translate(arg, ctx) for arg in event.type.arg_types]
            event_args = [self.viper_ast.LocalVarDecl(ctx.new_local_var_name('$arg'), arg_type, pos)
                          for arg_type in viper_types]
            ctx.new_local_vars.extend(event_args)
            local_args = [arg.localVar() for arg in event_args]
            ctx.event_vars[event_name] = local_args

            # Inhale zero or more times write permission

            # PermMul variable for unknown permission amount
            var_name = ctx.new_local_var_name('$a')
            var_decl = self.viper_ast.LocalVarDecl(var_name, self.viper_ast.Int, pos)
            ctx.new_local_vars.append(var_decl)
            var_perm_mul = var_decl.localVar()
            ge_zero_cond = self.viper_ast.GeCmp(var_perm_mul, self.viper_ast.IntLit(0, pos), pos)
            assume_ge_zero = self.viper_ast.Inhale(ge_zero_cond, pos)

            # PredicateAccessPredicate
            pred_acc = self.viper_ast.PredicateAccess(local_args, event_name, pos)
            perm_mul = self.viper_ast.IntPermMul(var_perm_mul, self.viper_ast.FullPerm(pos), pos)
            pred_acc_pred = self.viper_ast.PredicateAccessPredicate(pred_acc, perm_mul, pos)
            log_event = self.viper_ast.Inhale(pred_acc_pred, pos)

            # Append both Inhales
            res.extend([assume_ge_zero, log_event])

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
                lhs = arg_var.local_var(ctx)
                if (types.is_numeric(arg_var.type)
                        and self.arithmetic_translator.is_wrapped(arg)
                        and self.arithmetic_translator.is_unwrapped(lhs)):
                    arg_var.is_local = False
                    lhs = arg_var.local_var(ctx)
                elif (types.is_numeric(arg_var.type)
                      and self.arithmetic_translator.is_unwrapped(arg)
                      and self.arithmetic_translator.is_wrapped(lhs)):
                    arg = helpers.w_wrap(self.viper_ast, arg)
                elif (not types.is_numeric(arg_var.type)
                      and self.arithmetic_translator.is_wrapped(arg)):
                    arg = helpers.w_unwrap(self.viper_ast, arg)
                ctx.new_local_vars.append(arg_var.var_decl(ctx))
                body.append(self.viper_ast.LocalVarAssign(arg_var.local_var(ctx), arg, apos))

            # Add result variable
            if function.type.return_type:
                ret_name = ctx.inline_prefix + mangled.RESULT_VAR
                ret_pos = return_value.pos()
                ctx.result_var = TranslatedVar(names.RESULT, ret_name, function.type.return_type,
                                               self.viper_ast, ret_pos, is_local=False)
                ctx.new_local_vars.append(ctx.result_var.var_decl(ctx, ret_pos))

                if (types.is_numeric(function.type.return_type)
                        and self.arithmetic_translator.is_unwrapped(return_value)):
                    return_value = helpers.w_wrap(self.viper_ast, return_value)
                body.append(self.viper_ast.LocalVarAssign(ctx.result_var.local_var(ret_pos), return_value, ret_pos))

            # Add success variable
            succ_name = ctx.inline_prefix + mangled.SUCCESS_VAR
            succ_var = TranslatedVar(names.SUCCESS, succ_name, types.VYPER_BOOL, self.viper_ast, succ.pos())
            ctx.new_local_vars.append(succ_var.var_decl(ctx))
            ctx.success_var = succ_var
            body.append(self.viper_ast.LocalVarAssign(succ_var.local_var(ctx), succ, succ.pos()))

            translate = self.spec_translator.translate_pre_or_postcondition
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
