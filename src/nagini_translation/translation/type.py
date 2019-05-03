"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Optional

from nagini_translation.ast import types
from nagini_translation.ast.types import VyperType, PrimitiveType, MapType

from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import Type, Expr, Stmt, StmtsAndExpr

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.context import Context
from nagini_translation.translation.builtins import map_type, map_init


class TypeTranslator(NodeTranslator):

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
        else:
            return self.viper_ast.Ref

    def revert(self, type: VyperType, field, ctx: Context) -> [Stmt]:
        nopos = self.no_position()
        info = self.no_info()

        def old(ref, field):
            field_acc = self.viper_ast.FieldAccess(ref, field, nopos, info)
            old = self.viper_ast.Old(field_acc, nopos, info)
            return self.viper_ast.FieldAssign(field_acc, old, nopos, info)

        self_var = ctx.self_var.localVar()
        return [old(self_var, field)]

    def translate_default_value(self, type: VyperType, ctx: Context) -> StmtsAndExpr:
        pos = self.no_position()
        info = self.no_info()

        if type is types.VYPER_BOOL:
            return [], self.viper_ast.FalseLit(pos, info)
        elif isinstance(type, PrimitiveType):
            return [], self.viper_ast.IntLit(0, pos, info)
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)

            stmts, value_default = self.translate_default_value(type.value_type, ctx)
            call = map_init(self.viper_ast, value_default, key_type, value_type, pos, info)
            return [], call
        else:
            # TODO:
            assert False