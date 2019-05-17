"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.ast import names

from nagini_translation.lib.typedefs import StmtsAndExpr
from nagini_translation.lib.viper_ast import ViperAST

from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.context import Context, quantified_var_scope, inside_old_scope
from nagini_translation.translation.builtins import map_sum

from nagini_translation.translation import builtins

from nagini_translation.errors.translation import InvalidProgramException


class SpecificationTranslator(ExpressionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self._invariant_mode = None
        # We require history invariants to be reflexive, therefore we can simply
        # replace old expressions by their expression in preconditions and in the
        # postcondition of __init__
        self._ignore_old = None

    def translate_precondition(self, pre: ast.AST, ctx: Context):
        self._invariant_mode = False
        self._ignore_old = True
        return self._translate_spec(pre, ctx)

    def translate_postcondition(self, post: ast.AST, ctx: Context, is_init=False):
        self._invariant_mode = False
        self._ignore_old = is_init
        return self._translate_spec(post, ctx)

    def translate_invariant(self, inv: ast.AST, ctx: Context, is_pre=False, is_init=False):
        # Invariants do not have to hold before __init__
        if is_pre and is_init:
            return None

        self._invariant_mode = True
        self._ignore_old = is_pre or is_init
        expr = self._translate_spec(inv, ctx)

        # Invariants of __init__ only have to hold if it succeeds
        if not is_pre and is_init:
            success_var = ctx.success_var
            succ = self.viper_ast.LocalVar(success_var.name(), success_var.typ(), expr.pos())
            return self.viper_ast.Implies(succ, expr, expr.pos())
        else:
            return expr

    def _translate_spec(self, node, ctx: Context):
        _, expr = self.translate(node, ctx)
        return expr

    def translate_Name(self, node: ast.Name, ctx: Context) -> StmtsAndExpr:
        if self._invariant_mode and node.id == names.MSG:
            assert False  # TODO: handle
        elif not self._ignore_old and not ctx.use_old and ctx.inside_old and node.id == names.SELF:
            pos = self.to_position(node, ctx)
            return [], builtins.old_self_var(self.viper_ast, pos).localVar()
        else:
            return super().translate_Name(node, ctx)

    def translate_Call(self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        assert isinstance(node.func, ast.Name)  # TODO: handle

        pos = self.to_position(node, ctx)

        name = node.func.id
        if name == names.IMPLIES:
            if len(node.args) != 2:
                raise InvalidProgramException(node, "Implication requires 2 arguments.")

            lhs = self._translate_spec(node.args[0], ctx)
            rhs = self._translate_spec(node.args[1], ctx)

            implies = self.viper_ast.Or(self.viper_ast.Not(lhs, pos), rhs, pos)
            return [], implies
        elif name == names.FORALL:
            with quantified_var_scope(ctx):
                num_args = len(node.args)
                # The first argument to forall is the variable declaration dict
                for name in node.args[0].keys:
                    name_pos = self.to_position(name, ctx)
                    type = self.type_translator.translate(name.type, ctx)
                    var_decl = self.viper_ast.LocalVarDecl(name.id, type, name_pos)
                    ctx.quantified_vars[name.id] = var_decl
                    ctx.all_vars[name.id] = var_decl

                # The last argument to forall is the quantified expression
                expr = self._translate_spec(node.args[num_args - 1], ctx)

                # The arguments in the middle are the triggers
                triggers = []
                for arg in node.args[1: num_args - 2]:
                    trigger_pos = self.to_position(arg, ctx)
                    trigger_exprs = [self._translate_spec(t, ctx) for t in arg.elts]
                    trigger = self.viper_ast.Trigger(trigger_exprs, trigger_pos)
                    triggers.append(trigger)

                quants = ctx.quantified_vars.values()
                return [], self.viper_ast.Forall(quants, triggers, expr, pos)
        elif name == names.RESULT or name == names.SUCCESS:
            cap = name.capitalize()
            if self._invariant_mode:
                raise InvalidProgramException(node, f"{cap} not allowed in invariant.")
            if node.args:
                raise InvalidProgramException(node, f"{cap} must not have arguments.")

            var = ctx.result_var if name == names.RESULT else ctx.success_var
            local_var = self.viper_ast.LocalVar(var.name(), var.typ(), pos)
            return [], local_var
        elif name == names.OLD:
            if len(node.args) != 1:
                raise InvalidProgramException(node, "Old expression requires a single argument.")

            arg = node.args[0]
            with inside_old_scope(ctx):
                expr = self._translate_spec(arg, ctx)
            if self._ignore_old or not ctx.use_old:
                return [], expr
            else:
                if ctx.old_label:
                    return [], self.viper_ast.LabelledOld(expr, ctx.old_label.name(), pos)
                else:
                    return [], self.viper_ast.Old(expr, pos)
        elif name == names.SUM:
            if len(node.args) != 1:
                raise InvalidProgramException(node, "Sum expression requires a single argument.")

            arg = node.args[0]
            expr = self._translate_spec(arg, ctx)
            key_type = self.type_translator.translate(arg.type.key_type, ctx)

            return [], map_sum(self.viper_ast, expr, key_type, pos)
        elif name == names.SENT:
            sent_acc = builtins.self_sent_field_acc(self.viper_ast, pos)
            if not node.args:
                return [], sent_acc
            else:
                arg_stmts, arg = self.translate(node.args[0], ctx)
                return arg_stmts, builtins.self_sent_map_get(self.viper_ast, arg, pos)
        elif name not in names.NOT_ALLOWED_IN_SPEC:
            return super().translate_Call(node, ctx)
        else:
            raise InvalidProgramException(node, f"Call to function {name} not allowed in specification.")
