"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Optional, Tuple

from twovyper.ast import names
from twovyper.ast.types import StructType

from twovyper.translation import helpers, mangled
from twovyper.translation.context import Context
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.type import TypeTranslator

from twovyper.verification.error import ModelTransformation

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Stmt


class ModelTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

        self.type_translator = TypeTranslator(viper_ast)

    def save_variables(self, ctx: Context, pos=None) -> Tuple[List[Stmt], ModelTransformation]:
        if not ctx.options.create_model:
            return [], None

        self_var = ctx.self_var.localVar()
        stmts = []
        transform = {}

        def add_model_var(name, var_type, rhs, components):
            new_var_name = ctx.new_local_var_name(mangled.model_var_name(*components))
            new_var = self.viper_ast.LocalVarDecl(new_var_name, var_type, pos)
            ctx.new_local_vars.append(new_var)
            transform[new_var_name] = name
            stmts.append(self.viper_ast.LocalVarAssign(new_var.localVar(), rhs, pos))

        def add_struct_members(struct_type, components):
            for member, member_type in struct_type.member_types.items():
                new_components = components + [member]
                if isinstance(member_type, StructType):
                    add_struct_members(member_type, new_components)
                else:
                    mtype = self.type_translator.translate(member_type, ctx)
                    get = helpers.struct_get(self.viper_ast, self_var, member, mtype, struct_type, pos)

                    if member == mangled.SELFDESTRUCT_FIELD:
                        name = f'{names.SELFDESTRUCT}()'
                    elif member == mangled.SENT_FIELD:
                        name = f'{names.SENT}()'
                    elif member == mangled.RECEIVED_FIELD:
                        name = f'{names.RECEIVED}()'
                    else:
                        name = '.'.join(new_components)

                    add_model_var(name, mtype, get, new_components)

        add_struct_members(ctx.program.type, [names.SELF])

        for arg_name, arg_var in ctx.args.items():
            transform[arg_var.name()] = arg_name

        for local_name, local_var in ctx.locals.items():
            transform[local_var.name()] = local_name

        transform[ctx.success_var.name()] = f'{names.SUCCESS}()'
        if ctx.result_var:
            transform[ctx.result_var.name()] = f'{names.RESULT}()'

        transform[mangled.OUT_OF_GAS] = f'{names.SUCCESS_OUT_OF_GAS}()'
        transform[mangled.MSG_SENDER_CALL_FAIL] = f'{names.SUCCESS_SENDER_FAILED}()'
        transform[mangled.OVERFLOW] = f'{names.SUCCESS_OVERFLOW}()'

        def model_transformation(name: str, value: str) -> Optional[Tuple[str, str]]:
            transformed_name = transform.get(name)
            if transformed_name is None:
                return None
            else:
                return transformed_name, value

        return stmts, model_transformation
