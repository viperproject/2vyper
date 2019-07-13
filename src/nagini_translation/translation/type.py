"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Optional, List

from nagini_translation.ast import types
from nagini_translation.ast.types import VyperType, PrimitiveType, MapType, ArrayType, StructType

from nagini_translation.translation.abstract import PositionTranslator, CommonTranslator
from nagini_translation.translation.context import Context, quantified_var_scope

from nagini_translation.translation.builtins import (
    array_type, array_init, array_get, map_type, map_init, map_get, map_sum, struct_type, struct_get, struct_init
)

from nagini_translation.viper.ast import ViperAST
from nagini_translation.viper.typedefs import Expr, Stmt, StmtsAndExpr, Type


class TypeTranslator(PositionTranslator, CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.type_dict = {
            types.VYPER_BOOL: viper_ast.Bool,
            types.VYPER_INT128: viper_ast.Int,
            types.VYPER_UINT256: viper_ast.Int,
            types.VYPER_WEI_VALUE: viper_ast.Int,
            types.VYPER_TIME: viper_ast.Int,
            types.VYPER_ADDRESS: viper_ast.Int,
            types.VYPER_BYTE: viper_ast.Int
        }

    def translate(self, type: VyperType, ctx: Context) -> Type:
        if isinstance(type, PrimitiveType):
            return self.type_dict[type]
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)
            return map_type(self.viper_ast, key_type, value_type)
        elif isinstance(type, ArrayType):
            element_type = self.translate(type.element_type, ctx)
            return array_type(self.viper_ast, element_type)
        elif isinstance(type, StructType):
            return struct_type(self.viper_ast, type)
        else:
            assert False

    def revert(self, type: VyperType, field, ctx: Context) -> [Stmt]:
        self_var = ctx.self_var.localVar()

        def old(ref, field):
            field_acc = self.viper_ast.FieldAccess(ref, field)
            old = self.viper_ast.Old(field_acc)
            return self.viper_ast.FieldAssign(field_acc, old)

        return [old(self_var, field)]

    def default_value(self, node: Optional, type: VyperType, ctx: Context) -> StmtsAndExpr:
        pos = self.no_position() if node is None else self.to_position(node, ctx)
        if type is types.VYPER_BOOL:
            return [], self.viper_ast.FalseLit(pos)
        elif isinstance(type, PrimitiveType):
            return [], self.viper_ast.IntLit(0, pos)
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)

            stmts, value_default = self.default_value(node, type.value_type, ctx)
            call = map_init(self.viper_ast, value_default, key_type, value_type, pos)
            return stmts, call
        elif isinstance(type, ArrayType):
            element_type = self.translate(type.element_type, ctx)
            stmts, element_default = self.default_value(node, type.element_type, ctx)
            array = array_init(self.viper_ast, element_default, type.size, element_type, pos)
            return stmts, array
        elif isinstance(type, StructType):
            init_args = {}
            stmts = []
            for name, member_type in type.arg_types.items():
                idx = type.arg_indices[name]
                default_stmts, val = self.default_value(node, member_type, ctx)
                init_args[idx] = val
                stmts.extend(default_stmts)
            args = [init_args[i] for i in range(len(init_args))]
            return stmts, struct_init(self.viper_ast, args, type, pos)
        else:
            assert False

    def non_negative(self, node, type: VyperType, ctx: Context) -> List[Expr]:
        """
        Computes the non-negativeness assumptions for a node `node` of type `type`.
        Node has to be a translated viper node.
        """

        return self._construct_quantifiers(node, type, ctx, 0)

    def array_length(self, node, type: VyperType, ctx: Context) -> List[Expr]:
        """
        Computes the array-length assumptions for a node `node` of type `type`.
        Node has to be a translated viper node.
        """

        return self._construct_quantifiers(node, type, ctx, 1)

    def _construct_quantifiers(self, node, type: VyperType, ctx: Context, mode: int) -> List[Expr]:
        """
        Computes the assumptions for either array length or non-negativeness of nested
        structures.

        If mode == 0: constructs non-negativeness
        If mode == 1: constructs array lengths
        """

        def construct(type, node):
            ret = []

            # If we encounter an unsigned primitive type we add the following assumption:
            #   x >= 0
            # where x is said integer
            if mode == 0 and types.is_unsigned(type):
                zero = self.viper_ast.IntLit(0)
                non_neg = self.viper_ast.GeCmp(node, zero)
                ret.append(non_neg)
            # If we encounter a map, we add the following assumptions:
            # In any mode:
            #   forall k: Key :: construct(map_get(k))
            # If mode == 0:
            #   forall k: Key :: map_get(k) <= map_sum()
            # where constuct constructs the assumption for the values contained
            # in the map (may be empty)
            elif isinstance(type, MapType):
                key_type = self.translate(type.key_type, ctx)
                value_type = self.translate(type.value_type, ctx)
                quant_var_name = ctx.new_quantified_var_name()
                quant_decl = self.viper_ast.LocalVarDecl(quant_var_name, key_type)
                quant = quant_decl.localVar()
                new_node = map_get(self.viper_ast, node, quant, key_type, value_type)
                trigger = self.viper_ast.Trigger([new_node])
                sub_ret = construct(type.value_type, new_node)
                for r in sub_ret:
                    quantifier = self.viper_ast.Forall([quant_decl], [trigger], r)
                    ret.append(quantifier)

                if mode == 0 and types.is_unsigned(type.value_type):
                    mp_sum = map_sum(self.viper_ast, node, key_type)
                    r = self.viper_ast.LeCmp(new_node, mp_sum)
                    quantifier = self.viper_ast.Forall([quant_decl], [trigger], r)
                    ret.append(quantifier)
            # If we encounter an array, we add the follwing assumptions:
            # If mode == 0:
            #   forall i: Int :: 0 <= i && i < |array| ==> construct(array[i]) >= 0
            # If mode == 1:
            #   forall i: Int :: 0 <= i && i < |array| ==> |array| == array_size
            #   forall i: Int :: 0 <= i && i < |array| ==> construct(array[i])
            # where construct recursively constructs the assumptions for nested arrays and maps
            elif isinstance(type, ArrayType):
                if mode == 1:
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
                new_node = array_get(self.viper_ast, node, quant, type.element_type)
                trigger = self.viper_ast.Trigger([new_node])

                leq = self.viper_ast.LeCmp(self.viper_ast.IntLit(0), quant)
                le = self.viper_ast.LtCmp(quant, self.viper_ast.SeqLength(node))
                bounds = self.viper_ast.And(leq, le)

                sub_ret = construct(type.element_type, new_node)
                for r in sub_ret:
                    implies = self.viper_ast.Implies(bounds, r)
                    quantifier = self.viper_ast.Forall([quant_decl], [trigger], implies)
                    ret.append(quantifier)
            # If we encounter a struct type we simply add the necessary assumptions for
            # all struct members
            elif isinstance(type, StructType):
                for member_name, member_type in type.arg_types.items():
                    viper_type = self.translate(member_type, ctx)
                    get = struct_get(self.viper_ast, node, member_name, viper_type, type)
                    ret.extend(construct(member_type, get))
            return ret

        with quantified_var_scope(ctx):
            return construct(type, node)

    def array_bounds_check(self, array, index, ctx: Context) -> Stmt:
        leq = self.viper_ast.LeCmp(self.viper_ast.IntLit(0), index)
        le = self.viper_ast.LtCmp(index, self.viper_ast.SeqLength(array))
        cond = self.viper_ast.Not(self.viper_ast.And(leq, le))
        return self.fail_if(cond, ctx)
