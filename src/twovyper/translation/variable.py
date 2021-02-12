"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Optional

from twovyper.translation import helpers

from twovyper.ast.types import VyperType

from twovyper.translation.context import Context
from twovyper.translation.type import TypeTranslator

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Var, VarDecl


class TranslatedVar:

    def __init__(self, vyper_name: str, viper_name: str, vyper_type: VyperType, viper_ast: ViperAST,
                 pos=None, info=None, is_local=True):
        self.name = vyper_name
        self.mangled_name = viper_name
        self.type = vyper_type
        self.viper_ast = viper_ast
        self.pos = pos
        self.info = info
        self.is_local = is_local
        self._type_translator = TypeTranslator(viper_ast)

    def var_decl(self, ctx: Context, pos=None, info=None) -> VarDecl:
        pos = pos or self.pos
        info = info or self.info
        vtype = self._type_translator.translate(self.type, ctx, is_local=self.is_local)
        return self.viper_ast.LocalVarDecl(self.mangled_name, vtype, pos, info)

    def local_var(self, ctx: Context, pos=None, info=None) -> Var:
        pos = pos or self.pos
        info = info or self.info
        vtype = self._type_translator.translate(self.type, ctx, is_local=self.is_local)
        return self.viper_ast.LocalVar(self.mangled_name, vtype, pos, info)


class TranslatedPureIndexedVar(TranslatedVar):

    def __init__(self, vyper_name: str, viper_name: str, vyper_type: VyperType, viper_ast: ViperAST,
                 pos=None, info=None, is_local=True):
        super().__init__(vyper_name, viper_name, vyper_type, viper_ast, pos, info, is_local)
        self.idx: Optional[int] = None
        self.viper_struct_type = helpers.struct_type(self.viper_ast)
        self.function_result = self.viper_ast.Result(self.viper_struct_type)

    def var_decl(self, ctx: Context, pos=None, info=None) -> VarDecl:
        pos = pos or self.pos
        info = info or self.info
        return self.viper_ast.TrueLit(pos, info)

    def local_var(self, ctx: Context, pos=None, info=None) -> Expr:
        pos = pos or self.pos
        info = info or self.info
        self.evaluate_idx(ctx)
        viper_type = self._type_translator.translate(self.type, ctx, is_local=self.is_local)
        return helpers.struct_get_idx(self.viper_ast, self.function_result, self.idx, viper_type, pos, info)

    def evaluate_idx(self, ctx: Context) -> int:
        if not self.idx:
            self.idx = ctx.next_pure_var_index()
        return self.idx

    def new_idx(self):
        self.idx = None
