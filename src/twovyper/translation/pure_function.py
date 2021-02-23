"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from functools import reduce
from itertools import chain
from typing import List

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.nodes import VyperFunction, VyperVar

from twovyper.translation import helpers, mangled
from twovyper.translation.context import Context
from twovyper.translation.function import FunctionTranslator
from twovyper.translation.pure_statement import PureStatementTranslator
from twovyper.translation.pure_translators import PureTranslatorMixin, PureTypeTranslator
from twovyper.translation.variable import TranslatedPureIndexedVar, TranslatedVar

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Function, Expr


class PureFunctionTranslator(PureTranslatorMixin, FunctionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.statement_translator = PureStatementTranslator(viper_ast)
        self.type_translator = PureTypeTranslator(viper_ast)

    def translate(self, function: VyperFunction, ctx: Context) -> Function:
        with ctx.function_scope():
            pos = self.to_position(function.node, ctx)

            ctx.function = function
            ctx.is_pure_function = True

            args = {name: self._translate_pure_non_local_var(var, ctx) for name, var in function.args.items()}
            state = {names.SELF: TranslatedVar(names.SELF, mangled.present_state_var_name(names.SELF),
                                               types.AnyStructType(), self.viper_ast, pos)}
            ctx.present_state = state
            ctx.old_state = ctx.present_state
            ctx.pre_state = ctx.present_state
            ctx.issued_state = ctx.present_state
            ctx.current_state = ctx.present_state
            ctx.current_old_state = ctx.present_state

            ctx.args = args.copy()
            ctx.locals = {}

            ctx.success_var = TranslatedPureIndexedVar(names.SUCCESS, mangled.SUCCESS_VAR,
                                                       types.VYPER_BOOL, self.viper_ast)

            ctx.return_label = None
            ctx.revert_label = None

            ctx.result_var = TranslatedPureIndexedVar(names.RESULT, mangled.RESULT_VAR,
                                                      function.type.return_type, self.viper_ast)

            body = []

            # State type assumptions
            for state_var in ctx.present_state.values():
                type_assumptions = self.type_translator.type_assumptions(state_var.local_var(ctx), state_var.type, ctx)
                body.extend(type_assumptions)

            # Assume type assumptions for self address
            self_address = helpers.self_address(self.viper_ast)
            self_address_ass = self.type_translator.type_assumptions(self_address, types.VYPER_ADDRESS, ctx)
            body.extend(self_address_ass)

            # Assume type assumptions for arguments
            for var in function.args.values():
                local_var = args[var.name].local_var(ctx)
                assumptions = self.type_translator.type_assumptions(local_var, var.type, ctx)
                body.extend(assumptions)

            # If we do not encounter an exception we will return success
            ctx.success_var.new_idx()
            body.append(self.viper_ast.EqCmp(ctx.success_var.local_var(ctx), self.viper_ast.TrueLit()))

            self.statement_translator.translate_stmts(function.node.body, body, ctx)

            viper_struct_type = helpers.struct_type(self.viper_ast)
            function_result = self.viper_ast.Result(viper_struct_type)

            def partial_unfinished_cond_expression(cond_and_idx):
                cond, idx = cond_and_idx

                def unfinished_cond_expression(expr):
                    val = helpers.struct_get_idx(self.viper_ast, function_result, idx, viper_type, pos)
                    return self.viper_ast.CondExp(cond, val, expr)

                return unfinished_cond_expression

            # Generate success variable
            viper_type = self.viper_ast.Bool
            unfinished_cond_expressions = list(map(partial_unfinished_cond_expression, ctx.pure_success))
            value = reduce(lambda expr, func: func(expr), reversed(unfinished_cond_expressions),
                           self.viper_ast.TrueLit())
            # Set success variable at slot 0
            success_var = helpers.struct_pure_get_success(self.viper_ast, function_result, pos)
            success_cond_expr = self.viper_ast.CondExp(value,
                                                       self.viper_ast.TrueLit(), self.viper_ast.FalseLit())
            body.append(self.viper_ast.EqCmp(success_var, success_cond_expr))

            # Generate result variable
            viper_type = self.viper_ast.Bool
            default_value = self.viper_ast.TrueLit()
            if function.type.return_type:
                viper_type = self.type_translator.translate(function.type.return_type, ctx)
                default_value = self.type_translator.default_value(function.node, function.type.return_type, body, ctx)
            unfinished_cond_expressions = list(map(partial_unfinished_cond_expression, ctx.pure_returns))
            value = reduce(lambda expr, func: func(expr), reversed(unfinished_cond_expressions), default_value)
            # Set result variable at slot 1
            result_var = helpers.struct_pure_get_result(self.viper_ast, function_result, viper_type, pos)
            body.append(self.viper_ast.EqCmp(result_var, value))

            # Arguments have to be TranslatedVar. Therefore, transform the non-local TranslatedPureIndexedVar to
            # local TranslatedVar.
            arg_transform = []
            new_args = {}
            for arg_name, arg in args.items():
                assert isinstance(arg, TranslatedPureIndexedVar)
                if not arg.is_local:
                    lhs = arg.local_var(ctx)
                    new_arg = TranslatedVar(arg.name, arg.mangled_name, arg.type, arg.viper_ast,
                                            arg.pos, arg.info, is_local=True)
                    rhs = new_arg.local_var(ctx)
                    arg_transform.append(self.viper_ast.EqCmp(lhs, rhs))
                    new_args[arg_name] = new_arg
            body = arg_transform + body
            args_list = [arg.var_decl(ctx) for arg in chain(state.values(), new_args.values())]

            viper_name = mangled.pure_function_name(function.name)
            function = self.viper_ast.Function(viper_name, args_list, helpers.struct_type(self.viper_ast),
                                               [], body, None, pos)
            return function

    def _translate_pure_non_local_var(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)
        name = mangled.local_var_name(ctx.inline_prefix, var.name)
        return TranslatedPureIndexedVar(var.name, name, var.type, self.viper_ast, pos, is_local=False)

    def inline(self, call: ast.ReceiverCall, args: List[Expr], res: List[Expr], ctx: Context) -> Expr:
        return self._call_pure(call, args, res, ctx)
