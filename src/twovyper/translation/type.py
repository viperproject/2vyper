"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from functools import reduce
from typing import Optional, List

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.types import (
    VyperType, PrimitiveType, MapType, ArrayType, TupleType, AnyStructType, StructType, ContractType, InterfaceType
)

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt, Type

from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context

from twovyper.translation import helpers, mangled


class TypeTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        wrapped_int_type = helpers.wrapped_int_type(self.viper_ast)
        self.wrapped_type_dict = {
            types.VYPER_BOOL: viper_ast.Bool,
            types.VYPER_INT128: wrapped_int_type,
            types.VYPER_UINT256: wrapped_int_type,
            types.VYPER_DECIMAL: wrapped_int_type,
            types.VYPER_ADDRESS: viper_ast.Int,
            types.VYPER_BYTE: viper_ast.Int,
            types.NON_NEGATIVE_INT: viper_ast.Int
        }
        self.type_dict = {
            types.VYPER_BOOL: viper_ast.Bool,
            types.VYPER_INT128: viper_ast.Int,
            types.VYPER_UINT256: viper_ast.Int,
            types.VYPER_DECIMAL: viper_ast.Int,
            types.VYPER_ADDRESS: viper_ast.Int,
            types.VYPER_BYTE: viper_ast.Int,
            types.NON_NEGATIVE_INT: viper_ast.Int
        }

    def translate(self, type: VyperType, ctx: Context, is_local=True) -> Type:
        if isinstance(type, PrimitiveType):
            if is_local:
                return self.type_dict[type]
            else:
                return self.wrapped_type_dict[type]
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)
            return helpers.map_type(self.viper_ast, key_type, value_type)
        elif isinstance(type, ArrayType):
            element_type = self.translate(type.element_type, ctx)
            return helpers.array_type(self.viper_ast, element_type)
        elif isinstance(type, (AnyStructType, StructType)):
            return helpers.struct_type(self.viper_ast)
        elif isinstance(type, (ContractType, InterfaceType)):
            return self.translate(types.VYPER_ADDRESS, ctx)
        elif isinstance(type, TupleType):
            return helpers.struct_type(self.viper_ast)
        else:
            assert False

    def default_value(self, node: Optional[ast.Node], type: VyperType, res: List[Stmt],
                      ctx: Context, is_local=True) -> Expr:
        pos = self.no_position() if node is None else self.to_position(node, ctx)
        if type is types.VYPER_BOOL:
            return self.viper_ast.FalseLit(pos)
        elif isinstance(type, PrimitiveType):
            if is_local:
                return self.viper_ast.IntLit(0, pos)
            else:
                return helpers.w_wrap(self.viper_ast, self.viper_ast.IntLit(0, pos), pos)
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)

            value_default = self.default_value(node, type.value_type, res, ctx)
            return helpers.map_init(self.viper_ast, value_default, key_type, value_type, pos)
        elif isinstance(type, ArrayType):
            sizes = [type.size]
            curr_type = type
            while isinstance(curr_type.element_type, ArrayType):
                # noinspection PyUnresolvedReferences
                sizes.append(curr_type.element_type.size)
                curr_type = curr_type.element_type
            element_type = self.translate(curr_type.element_type, ctx)
            if type.is_strict:
                result = self.default_value(node, curr_type.element_type, res, ctx)
                result_type = element_type
                for size in sizes:
                    result = helpers.array_init(self.viper_ast, result, size, result_type, pos)
                    result_type = helpers.array_type(self.viper_ast, result_type)
                return result
            else:
                return helpers.empty_array(self.viper_ast, element_type, pos)
        elif isinstance(type, StructType):
            init_args = {}
            for name, member_type in type.member_types.items():
                idx = type.member_indices[name]
                val = self.default_value(node, member_type, res, ctx)
                init_args[idx] = val
            args = [init_args[i] for i in range(len(init_args))]
            return helpers.struct_init(self.viper_ast, args, type, pos)
        elif isinstance(type, (ContractType, InterfaceType)):
            return self.default_value(node, types.VYPER_ADDRESS, res, ctx)
        elif isinstance(type, TupleType):
            return helpers.havoc_var(self.viper_ast, helpers.struct_type(self.viper_ast), ctx)
        else:
            assert False

    def type_assumptions(self, node, type: VyperType, ctx: Context) -> List[Expr]:
        """
        Computes the assumptions for either array length or number bounds of nested
        structures.

        If mode == 0: constructs bounds
        If mode == 1: constructs array lengths
        """

        def construct(type, node):
            ret = []

            # If we encounter a bounded primitive type we add the following assumption:
            #   x >= lower
            #   x <= upper
            # where x is said integer
            if types.is_bounded(type):
                lower = self.viper_ast.IntLit(type.lower)
                upper = self.viper_ast.IntLit(type.upper)
                lcmp = self.viper_ast.LeCmp(lower, node)
                ucmp = self.viper_ast.LeCmp(node, upper)
                # If the no_overflows config option is enabled, we only assume non-negativity for uints
                if ctx.program.config.has_option(names.CONFIG_NO_OVERFLOWS):
                    if types.is_unsigned(type):
                        bounds = lcmp
                    else:
                        bounds = self.viper_ast.TrueLit()
                else:
                    bounds = self.viper_ast.And(lcmp, ucmp)
                ret.append(bounds)
            elif type == types.NON_NEGATIVE_INT:
                lower = self.viper_ast.IntLit(0)
                lcmp = self.viper_ast.LeCmp(lower, node)
                ret.append(lcmp)
            # If we encounter a map, we add the following assumptions:
            #   forall k: Key :: construct(map_get(k))
            #   forall k: Key :: map_get(k) <= map_sum()
            # where constuct constructs the assumption for the values contained
            # in the map (may be empty)
            elif isinstance(type, MapType):
                key_type = self.translate(type.key_type, ctx)
                value_type = self.translate(type.value_type, ctx)
                quant_var_name = ctx.new_quantified_var_name()
                quant_decl = self.viper_ast.LocalVarDecl(quant_var_name, key_type)
                quant = quant_decl.localVar()
                new_node = helpers.map_get(self.viper_ast, node, quant, key_type, value_type)
                trigger = self.viper_ast.Trigger([new_node])
                sub_ret = construct(type.value_type, new_node)
                for r in sub_ret:
                    quantifier = self.viper_ast.Forall([quant_decl], [trigger], r)
                    ret.append(quantifier)

                if types.is_unsigned(type.value_type):
                    mp_sum = helpers.map_sum(self.viper_ast, node, key_type)
                    r = self.viper_ast.LeCmp(new_node, mp_sum)
                    quantifier = self.viper_ast.Forall([quant_decl], [trigger], r)
                    ret.append(quantifier)
            # If we encounter an array, we add the follwing assumptions:
            #   |array| == array_size
            #   forall i: Int :: 0 <= i && i < |array| ==> construct(array[i])
            # where construct recursively constructs the assumptions for nested arrays and maps
            elif isinstance(type, ArrayType):
                array_len = self.viper_ast.SeqLength(node)
                size = self.viper_ast.IntLit(type.size)
                if type.is_strict:
                    comp = self.viper_ast.EqCmp(array_len, size)
                else:
                    comp = self.viper_ast.LeCmp(array_len, size)
                ret.append(comp)

                quant_var_name = ctx.new_quantified_var_name()
                quant_decl = self.viper_ast.LocalVarDecl(quant_var_name, self.viper_ast.Int)
                quant = quant_decl.localVar()
                new_node = helpers.array_get(self.viper_ast, node, quant, type.element_type)
                trigger = self.viper_ast.Trigger([new_node])

                leq = self.viper_ast.LeCmp(self.viper_ast.IntLit(0), quant)
                le = self.viper_ast.LtCmp(quant, self.viper_ast.SeqLength(node))
                bounds = self.viper_ast.And(leq, le)

                sub_ret = construct(type.element_type, new_node)
                for r in sub_ret:
                    implies = self.viper_ast.Implies(bounds, r)
                    quantifier = self.viper_ast.Forall([quant_decl], [trigger], implies)
                    ret.append(quantifier)
            elif isinstance(type, (ContractType, InterfaceType)):
                return construct(types.VYPER_ADDRESS, node)
            # If we encounter a struct type we simply add the necessary assumptions for
            # all struct members
            # Additionally, we add an assumption about the type tag
            elif isinstance(type, StructType):
                for member_name, member_type in type.member_types.items():
                    viper_type = self.translate(member_type, ctx)
                    get = helpers.struct_get(self.viper_ast, node, member_name, viper_type, type)
                    ret.extend(construct(member_type, get))

                type_tag = self.viper_ast.IntLit(mangled.struct_type_tag(type.name, type.kind))
                get_tag = helpers.struct_type_tag(self.viper_ast, node)
                ret.append(self.viper_ast.EqCmp(get_tag, type_tag))

            return ret

        with ctx.quantified_var_scope():
            return construct(type, node)

    def array_bounds_check(self, array, index, res: List[Stmt], ctx: Context):
        leq = self.viper_ast.LeCmp(self.viper_ast.IntLit(0), index)
        le = self.viper_ast.LtCmp(index, self.viper_ast.SeqLength(array))
        cond = self.viper_ast.Not(self.viper_ast.And(leq, le))
        self.fail_if(cond, [], res, ctx)

    def comparator(self, type: VyperType, ctx: Context):
        # For msg, block, chain, tx we don't generate an equality function, as they are immutable anyway
        if isinstance(type, StructType) and type not in names.ENV_VARIABLES:
            return mangled.struct_eq_name(type.name, type.kind), {}
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)
            type_map = helpers._map_type_var_map(self.viper_ast, key_type, value_type)
            return mangled.MAP_EQ, type_map
        else:
            return None

    def eq(self, left, right, type: VyperType, ctx: Context, pos=None) -> Expr:
        if isinstance(type, StructType):
            return helpers.struct_eq(self.viper_ast, left, right, type, pos)
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)
            return helpers.map_eq(self.viper_ast, left, right, key_type, value_type, pos)
        elif isinstance(type, TupleType):
            cond = None
            for idx, element_type in enumerate(type.element_types):
                viper_type = self.translate(element_type, ctx)
                left_element = helpers.struct_get_idx(self.viper_ast, left, idx, viper_type, pos)
                right_element = helpers.struct_get_idx(self.viper_ast, right, idx, viper_type, pos)
                element_cond = self.viper_ast.EqCmp(left_element, right_element, pos)
                cond = self.viper_ast.And(cond, element_cond, pos) if cond else element_cond
            return cond
        else:
            return self.viper_ast.EqCmp(left, right, pos)

    def neq(self, left, right, type: VyperType, ctx: Context, pos=None) -> Expr:
        if isinstance(type, StructType):
            return self.viper_ast.Not(helpers.struct_eq(self.viper_ast, left, right, type, pos), pos)
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)
            map_eq = helpers.map_eq(self.viper_ast, left, right, key_type, value_type, pos)
            return self.viper_ast.Not(map_eq, pos)
        elif isinstance(type, TupleType):
            cond = None
            for idx, element_type in enumerate(type.element_types):
                viper_type = self.translate(element_type, ctx)
                left_element = helpers.struct_get_idx(self.viper_ast, left, idx, viper_type, pos)
                right_element = helpers.struct_get_idx(self.viper_ast, right, idx, viper_type, pos)
                element_cond = self.viper_ast.NeCmp(left_element, right_element, pos)
                cond = self.viper_ast.Or(cond, element_cond, pos) if cond else element_cond
            return cond
        else:
            return self.viper_ast.NeCmp(left, right, pos)
