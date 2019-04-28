"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Optional

from nagini_translation.parsing.types import *

from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import Type, Expr, Stmt, StmtsAndExpr

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.context import Context
from nagini_translation.translation.builtins import MAP_INIT, map_acc, map_acc_field


class TypeTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.type_dict = {
            VYPER_BOOL: viper_ast.Bool, 
            VYPER_INT128: viper_ast.Int,
            VYPER_UINT256: viper_ast.Int, 
            VYPER_WEI_VALUE: viper_ast.Int,
            VYPER_ADDRESS: viper_ast.Int
        }

    def translate(self, type: VyperType, ctx: Context) -> Type:
        if isinstance(type, PrimitiveType):
            return self.type_dict[type]
        else:
            return self.viper_ast.Ref

    # TODO: This method seems very weird, change it once more permissions are needed for other
    # types, else integrate it into translator
    def permissions(self, type: VyperType, field, ctx: Context) -> Optional[Expr]:
        pos = self.no_position()
        info = self.no_info()

        if isinstance(type, PrimitiveType):
            return None
        elif isinstance(type, MapType):
            field_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), field, pos, info)
            return map_acc(self.viper_ast, field_acc, pos, info)
        else:
            # TODO: handle other?
            assert False

    def revert(self, type: VyperType, field, ctx: Context) -> [Stmt]:
        nopos = self.no_position()
        info = self.no_info()

        def old(ref, field):
            field_acc = self.viper_ast.FieldAccess(ref, field, nopos, info)
            old = self.viper_ast.Old(field_acc, nopos, info)
            return self.viper_ast.FieldAssign(field_acc, old, nopos, info)

        self_var = ctx.self_var.localVar()

        if isinstance(type, PrimitiveType):
            return [old(self_var, field)]
        elif isinstance(type, MapType):
            map_field_ref = self.viper_ast.FieldAccess(self_var, field, nopos, info)
            map_field = map_acc_field(self.viper_ast, nopos, info)
            return [old(self_var, field), old(map_field_ref, map_field)]
        

    def translate_default_value(self, type: VyperType, ctx: Context) -> StmtsAndExpr:
        pos = self.no_position()
        info = self.no_info()

        if type is VYPER_BOOL:
            return [], self.viper_ast.FalseLit(pos, info)
        elif isinstance(type, PrimitiveType):
            return [], self.viper_ast.IntLit(0, pos, info)
        elif isinstance(type, MapType):
            # TODO: only works for primitive int-to-int maps
            loc_name = ctx.new_local_var_name()
            loc_var = self.viper_ast.LocalVarDecl(loc_name, self.viper_ast.Ref, pos, info)
            ctx.new_local_vars.append(loc_var)
            call = self.viper_ast.MethodCall(MAP_INIT, [], [loc_var.localVar()], pos, info)
            return [call], loc_var.localVar()
        else:
            # TODO:
            assert False


    
