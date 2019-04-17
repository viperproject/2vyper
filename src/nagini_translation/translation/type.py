"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from nagini_translation.parsing.types import VyperType, VYPER_BOOL, VYPER_INT128, VYPER_UINT256, VYPER_WEI_VALUE
from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import Type


class TypeTranslator:

    def __init__(self, viper_ast: ViperAST):
        self.type_dict = {
            VYPER_BOOL: viper_ast.Bool, 
            VYPER_INT128: viper_ast.Int,
            VYPER_UINT256: viper_ast.Int, 
            VYPER_WEI_VALUE: viper_ast.Int
        }

    def translate(self, type: VyperType) -> Type:
        return self.type_dict[type]

    
