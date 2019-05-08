"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.utils import seq_to_list

from nagini_translation.lib.typedefs import Program
from nagini_translation.lib.viper_ast import ViperAST

from nagini_translation.ast import names
from nagini_translation.ast import types
from nagini_translation.ast.nodes import VyperProgram, VyperVar

from nagini_translation.translation.abstract import PositionTranslator
from nagini_translation.translation.function import FunctionTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.context import Context

from nagini_translation.translation import builtins


class ProgramTranslator(PositionTranslator):

    def __init__(self, viper_ast: ViperAST, builtins: Program):
        self.viper_ast = viper_ast
        self.builtins = builtins
        self.function_translator = FunctionTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def _translate_field(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)

        name = var.name
        type = self.type_translator.translate(var.type, ctx)
        field = self.viper_ast.Field(name, type, pos)

        return field

    def _create_field_access_predicate(self, field_access, amount, ctx: Context):
        if amount == 1:
            perm = self.viper_ast.FullPerm()
        else:
            perm = self.viper_ast.WildcardPerm()
        return self.viper_ast.FieldAccessPredicate(field_access, perm)

    def translate(self, vyper_program: VyperProgram, file: str) -> Program:
        if names.INIT not in vyper_program.functions:
            vyper_program.functions[builtins.INIT] = builtins.init_function()

        # Add built-in methods
        methods = seq_to_list(self.builtins.methods())
        # Add built-in functions
        domains = seq_to_list(self.builtins.domains())

        ctx = Context(file)
        ctx.program = vyper_program
        ctx.self_var = builtins.self_var(self.viper_ast)
        ctx.msg_var = builtins.msg_var(self.viper_ast)

        ctx.fields = {}
        ctx.immutable_fields = {}
        ctx.permissions = []
        ctx.unchecked_invariants = []
        for var in vyper_program.state.values():
            # Create field
            field = self._translate_field(var, ctx)
            ctx.fields[var.name] = field

            # Pass around the permissions for all fields
            field_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), field)
            acc = self._create_field_access_predicate(field_acc, 1, ctx)
            ctx.permissions.append(acc)

            if types.is_unsigned(var.type):
                zero = self.viper_ast.IntLit(0)
                non_neg = self.viper_ast.GeCmp(field_acc, zero)
                ctx.unchecked_invariants.append(non_neg)
            
            array_lens = self.type_translator.array_length(field_acc, var.type, ctx)
            ctx.unchecked_invariants.extend(array_lens)
        
        # Create msg.sender field
        msg_sender = builtins.msg_sender_field(self.viper_ast)
        ctx.immutable_fields[builtins.MSG_SENDER] = msg_sender
        # Pass around the permissions for msg.sender
        field_acc = self.viper_ast.FieldAccess(ctx.msg_var.localVar(), msg_sender)
        acc = self._create_field_access_predicate(field_acc, 0, ctx)
        ctx.permissions.append(acc)
        # Assume msg.sender != 0
        zero = self.viper_ast.IntLit(0)
        ctx.unchecked_invariants.append(self.viper_ast.NeCmp(field_acc, zero))

        fields_list = list(ctx.fields.values()) + list(ctx.immutable_fields.values())

        functions = vyper_program.functions.values()
        methods += [self.function_translator.translate(function, ctx) for function in functions]
        viper_program = self.viper_ast.Program(domains, fields_list, [], [], methods)
        return viper_program