"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from itertools import chain
from typing import List, Optional, Tuple

from twovyper.ast import names, types
from twovyper.ast.arithmetic import Decimal
from twovyper.ast.types import StructType, DecimalType

from twovyper.translation import helpers, mangled
from twovyper.translation.context import Context
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.type import TypeTranslator

from twovyper.verification.model import ModelTransformation

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Stmt


class ModelTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

        self.type_translator = TypeTranslator(viper_ast)

    def save_variables(self, res: List[Stmt], ctx: Context, pos=None) -> Optional[ModelTransformation]:
        # Viper only gives a model for variables, therefore we save all important expressions
        # in variables and provide a mapping back to the Vyper expression. Also, we give a value
        # transformation to change, e.g., 12 to 0.0000000012 for decimals.
        if not ctx.options.create_model:
            return [], None

        self_var = ctx.self_var.local_var(ctx)
        old_self_var = ctx.old_self_var.local_var(ctx)
        transform = {}
        type_map = {}

        def add_model_var(name, var_type, rhs, components):
            new_var_name = ctx.new_local_var_name(mangled.model_var_name(*components))
            vtype = self.type_translator.translate(var_type, ctx)
            new_var = self.viper_ast.LocalVarDecl(new_var_name, vtype, pos)
            ctx.new_local_vars.append(new_var)
            transform[new_var_name] = name
            type_map[new_var_name] = var_type
            if hasattr(rhs, 'isSubtype') and rhs.isSubtype(helpers.wrapped_int_type(self.viper_ast)):
                rhs = helpers.w_unwrap(self.viper_ast, rhs)
            res.append(self.viper_ast.LocalVarAssign(new_var.localVar(), rhs, pos))

        def add_struct_members(struct, struct_type, components, wrapped=None):
            for member, member_type in struct_type.member_types.items():
                new_components = components + [member]
                mtype = self.type_translator.translate(member_type, ctx)
                get = helpers.struct_get(self.viper_ast, struct, member, mtype, struct_type, pos)
                if isinstance(member_type, StructType):
                    add_struct_members(get, member_type, new_components, wrapped)
                else:
                    if member == mangled.SELFDESTRUCT_FIELD:
                        name = f'{names.SELFDESTRUCT}()'
                    elif member == mangled.SENT_FIELD:
                        name = f'{names.SENT}()'
                    elif member == mangled.RECEIVED_FIELD:
                        name = f'{names.RECEIVED}()'
                    else:
                        name = '.'.join(new_components)

                    if wrapped:
                        name = wrapped(name)

                    add_model_var(name, member_type, get, new_components)

        add_struct_members(self_var, ctx.program.type, [names.SELF])
        add_struct_members(old_self_var, ctx.program.type, [names.SELF], lambda n: f'{names.OLD}({n})')
        if ctx.function.analysis.uses_issued:
            issued_self_var = ctx.pre_self_var.local_var(ctx)
            add_struct_members(issued_self_var, ctx.program.type, [names.SELF], lambda n: f'{names.ISSUED}({n})')

        for var in chain(ctx.args.values(), ctx.locals.values()):
            if isinstance(var.type, StructType):
                add_struct_members(var.local_var(ctx), var.type, [var.name])
            else:
                transform[var.mangled_name] = var.name
                type_map[var.mangled_name] = var.type

        if ctx.success_var is not None:
            transform[ctx.success_var.mangled_name] = f'{names.SUCCESS}()'
            type_map[ctx.success_var.mangled_name] = ctx.success_var.type
        if ctx.result_var is not None:
            transform[ctx.result_var.mangled_name] = f'{names.RESULT}()'
            type_map[ctx.result_var.mangled_name] = ctx.result_var.type

        transform[mangled.OUT_OF_GAS] = f'{names.OUT_OF_GAS}()'
        type_map[mangled.OUT_OF_GAS] = types.VYPER_BOOL
        transform[mangled.OVERFLOW] = f'{names.OVERFLOW}()'
        type_map[mangled.OVERFLOW] = types.VYPER_BOOL

        return (transform, type_map)
