"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.parsing.types import VyperType
from nagini_translation.parsing.types import (
    VYPER_ADDRESS, VYPER_BOOL, VYPER_INT128, VYPER_UINT256, VYPER_WEI_VALUE
)

from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import StmtsAndExpr

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.context import Context


class DefaultValueTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self._numeric_types = [VYPER_ADDRESS, VYPER_INT128, VYPER_UINT256, VYPER_WEI_VALUE]

    def translate_default_value(self, type: VyperType, ctx: Context) -> StmtsAndExpr:
        pos = self.no_position()
        info = self.no_info()

        if type in self._numeric_types:
            return [], self.viper_ast.IntLit(0, pos, info)
        elif type is VYPER_BOOL:
            return [], self.viper_ast.FalseLit(pos, info)
        else:
            # TODO:
            assert False
