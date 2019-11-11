"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from twovyper.ast.types import VyperType

from twovyper.translation.context import Context
from twovyper.translation.type import TypeTranslator

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Var, VarDecl


class TranslatedVar:

    def __init__(self, vyper_name: str, viper_name: str, type: VyperType, viper_ast: ViperAST, pos=None, info=None):
        self.name = vyper_name
        self.mangled_name = viper_name
        self.type = type
        self.viper_ast = viper_ast
        self.pos = pos
        self.info = info
        self._type_translator = TypeTranslator(viper_ast)

    def var_decl(self, ctx: Context, pos=None, info=None) -> VarDecl:
        pos = pos or self.pos
        info = info or self.info
        vtype = self._type_translator.translate(self.type, ctx)
        return self.viper_ast.LocalVarDecl(self.mangled_name, vtype, pos, info)

    def local_var(self, ctx: Context, pos=None, info=None) -> Var:
        pos = pos or self.pos
        info = info or self.info
        vtype = self._type_translator.translate(self.type, ctx)
        return self.viper_ast.LocalVar(self.mangled_name, vtype, pos, info)
