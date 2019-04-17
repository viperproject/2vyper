"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.parsing.ast import VyperProgram, VyperFunction
from nagini_translation.lib.typedefs import Program
from nagini_translation.lib.viper_ast import ViperAST

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.function import FunctionTranslator


def translate(vyper_program: VyperProgram, viper_ast: ViperAST) -> Program:
    return ProgramTranslator(viper_ast).translate(vyper_program)


class ProgramTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.function_translator = FunctionTranslator(viper_ast)


    def translate(self, vyper_program: VyperProgram) -> Program:
        pos = self.no_position()
        info = self.no_info()
        functions = vyper_program.functions.values()
        methods = [self.function_translator.translate(function) for function in functions]
        viper_program = self.viper_ast.Program([], [], [], [], methods, pos, info)
        return viper_program