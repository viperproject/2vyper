"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Optional, List

from nagini_translation.ast import types
from nagini_translation.ast.types import VyperType, PrimitiveType, MapType, ArrayType

from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import Type, Expr, Stmt, StmtsAndExpr

from nagini_translation.translation.abstract import PositionTranslator
from nagini_translation.translation.context import Context, quantified_var_scope

from nagini_translation.translation.builtins import (
    array_type, array_init, array_get, map_type, map_init, map_get
)


class TypeTranslator(PositionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.type_dict = {
            types.VYPER_BOOL: viper_ast.Bool, 
            types.VYPER_INT128: viper_ast.Int,
            types.VYPER_UINT256: viper_ast.Int, 
            types.VYPER_WEI_VALUE: viper_ast.Int,
            types.VYPER_ADDRESS: viper_ast.Int
        }

    def translate(self, type: VyperType, ctx: Context) -> VyperType:
        if isinstance(type, PrimitiveType):
            return self.type_dict[type]
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)
            return map_type(self.viper_ast, key_type, value_type)
        elif isinstance(type, ArrayType):
            element_type = self.translate(type.element_type, ctx)
            return array_type(self.viper_ast, element_type)
        else:
            assert False # TODO: handle

    def revert(self, type: VyperType, field, ctx: Context) -> [Stmt]:
        self_var = ctx.self_var.localVar()

        def old(ref, field):
            field_acc = self.viper_ast.FieldAccess(ref, field)
            old = self.viper_ast.Old(field_acc)
            return self.viper_ast.FieldAssign(field_acc, old)

        return [old(self_var, field)]

    def default_value(self, node: Optional, type: VyperType, ctx: Context) -> StmtsAndExpr:
        pos = self.no_position() if node == None else self.to_position(node, ctx)
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
        else:
            # TODO:
            assert False

    def array_length(self, node, type: VyperType, ctx: Context) -> List[Expr]:
        """
        Computes the array-length assumptions for a node `node` of type `type`.
        Node has to be a translated viper node.
        """

        def construct(type, node):
            lens = []

            # If we encounter a map, we add the following assumption:
            #   forall k: Key :: construct(map_get(k))
            # where constuct constructs the size assumption for the array contained
            # in the map (may be empty)
            if isinstance(type, MapType):
                key_type = self.translate(type.key_type, ctx)
                value_type = self.translate(type.value_type, ctx)
                quant_var_name = ctx.new_quantified_var_name()
                quant_decl = self.viper_ast.LocalVarDecl(quant_var_name, key_type)
                quant = quant_decl.localVar()
                new_node = map_get(self.viper_ast, node, quant, key_type, value_type)
                trigger = self.viper_ast.Trigger([new_node])
                sub_lens = construct(type.value_type, new_node)
                for l in sub_lens:
                    quantifier = self.viper_ast.Forall([quant_decl], [trigger], l)
                    lens.append(quantifier)

            # If we encounter an array, we add the follwing assumptions:
            #   forall i: Int :: 0 <= i && i < |array| ==> |array| == array_size
            #   forall i: Int :: 0 <= i && i < |array| ==> construct(array[i])
            # where construct recursively constructs the assumptions for nested arrays and maps
            elif isinstance(type, ArrayType):
                array_len = self.viper_ast.SeqLength(node)
                size = self.viper_ast.IntLit(type.size)
                eq = self.viper_ast.EqCmp(array_len, size)
                lens.append(eq)

                quant_var_name = ctx.new_quantified_var_name()
                quant_decl = self.viper_ast.LocalVarDecl(quant_var_name, self.viper_ast.Int)
                quant = quant_decl.localVar()
                new_node = array_get(self.viper_ast, node, quant)
                trigger = self.viper_ast.Trigger([new_node])

                leq = self.viper_ast.LeCmp(self.viper_ast.IntLit(0), quant)
                le = self.viper_ast.LtCmp(quant, self.viper_ast.SeqLength(node))
                bounds = self.viper_ast.And(leq, le)

                sub_lens = construct(type.element_type, new_node)
                for l in sub_lens:
                    implies = self.viper_ast.Implies(bounds, l)
                    quantifier = self.viper_ast.Forall([quant_decl], [trigger], implies)
                    lens.append(quantifier)

            return lens

        with quantified_var_scope(ctx):
            lens = construct(type, node)
        return lens

    def _fail_if(self, cond, ctx: Context):
        body = [self.viper_ast.Goto(ctx.revert_label)]
        block = self.viper_ast.Seqn(body)
        empty = self.viper_ast.Seqn([])
        return self.viper_ast.If(cond, block, empty)

    def array_bounds_check(self, array, index, ctx: Context) -> Stmt:
        leq = self.viper_ast.LeCmp(self.viper_ast.IntLit(0), index)
        le = self.viper_ast.LtCmp(index, self.viper_ast.SeqLength(array))
        cond = self.viper_ast.Not(self.viper_ast.And(leq, le))
        return self._fail_if(cond, ctx)
