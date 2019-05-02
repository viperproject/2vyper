"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.utils import seq_to_list

from nagini_translation.parsing.ast import VyperProgram, VyperVar
from nagini_translation.lib.typedefs import Program
from nagini_translation.lib.viper_ast import ViperAST

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.function import FunctionTranslator
from nagini_translation.translation.type import TypeTranslator

from nagini_translation.translation.context import Context
from nagini_translation.translation.builtins import INIT
from nagini_translation.translation.builtins import init_function, self_var


class ProgramTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST, builtins: Program):
        self.viper_ast = viper_ast
        self.builtins = builtins
        self.function_translator = FunctionTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def _translate_field(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        info = self.no_info()

        name = var.name
        type = self.type_translator.translate(var.type, ctx)
        field = self.viper_ast.Field(name, type, pos, info)

        return field

    def _create_field_access_predicate(self, receiver, field, ctx: Context):
        pos = self.no_position()
        info = self.no_info()

        field_acc = self.viper_ast.FieldAccess(receiver, field, pos, info)
        perm = self.viper_ast.FullPerm(pos, info)
        return self.viper_ast.FieldAccessPredicate(field_acc, perm, pos, info)

    def translate(self, vyper_program: VyperProgram, file: str) -> Program:
        if INIT not in vyper_program.functions:
            vyper_program.functions[INIT] = init_function()
        pos = self.no_position()
        info = self.no_info()

        # Add built-in fields (for maps, etc.)
        builtin_fields = seq_to_list(self.builtins.fields())
        # Add built-in methods
        methods = seq_to_list(self.builtins.methods())
        # Add built-in functions
        domains = seq_to_list(self.builtins.domains())

        ctx = Context(file)
        ctx.program = vyper_program
        ctx.self_var = self_var(self.viper_ast, pos, info)

        ctx.fields = {}
        ctx.permissions = []
        for var in vyper_program.state.values():
            # Create field
            field = self._translate_field(var, ctx)
            ctx.fields[var.name] = field

            # Pass around the permissions for all fields
            acc = self._create_field_access_predicate(ctx.self_var.localVar(), field, ctx)
            ctx.permissions.append(acc)

        fields_list = builtin_fields + list(ctx.fields.values())

        functions = vyper_program.functions.values()
        methods += [self.function_translator.translate(function, ctx) for function in functions]
        viper_program = self.viper_ast.Program(domains, fields_list, [], [], methods, pos, info)
        return viper_program