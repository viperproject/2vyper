"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.ast import names

from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.context import Context
from nagini_translation.translation.context import quantified_var_scope, self_scope

from nagini_translation.translation import mangled
from nagini_translation.translation import helpers

from nagini_translation.exceptions import InvalidProgramException

from nagini_translation.viper.ast import ViperAST
from nagini_translation.viper.typedefs import StmtsAndExpr


class SpecificationTranslator(ExpressionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

    def translate_postcondition(self, post: ast.AST, ctx: Context, is_init=False):
        # For postconditions the old state is the state before the function call, except for
        # __init__ where we use the self state instead (since there is no pre-state)
        old_var = ctx.self_var if is_init else ctx.pre_self_var
        with self_scope(ctx.self_var, old_var, ctx):
            return self._translate_spec(post, ctx)

    def translate_check(self, check: ast.AST, ctx: Context, is_init=False, is_fail=False):
        # In a check we use the last publicly seen state as the old state except for __init__
        # where we use the normal self state instead
        old_var = ctx.self_var if is_init else ctx.old_self_var
        with self_scope(ctx.self_var, old_var, ctx):
            expr = self._translate_spec(check, ctx)
        if is_fail:
            # We evaluate the check on failure in the old heap because events didn't
            # happen there
            pos = self.to_position(check, ctx)
            return self.viper_ast.Old(expr, pos)
        else:
            return expr

    def translate_invariant(self, inv: ast.AST, ctx: Context):
        return self._translate_spec(inv, ctx)

    def _translate_spec(self, node, ctx: Context):
        _, expr = self.translate(node, ctx)
        return expr

    def translate_Call(self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        name = node.func.id
        if name == names.IMPLIES:
            # TODO: handle in different place
            if len(node.args) != 2:
                raise InvalidProgramException(node, "Implication requires 2 arguments.")

            lhs = self._translate_spec(node.args[0], ctx)
            rhs = self._translate_spec(node.args[1], ctx)

            return [], self.viper_ast.Implies(lhs, rhs, pos)
        elif name == names.FORALL:
            with quantified_var_scope(ctx):
                num_args = len(node.args)
                quants = []
                # The first argument to forall is the variable declaration dict
                for var_name in node.args[0].keys:
                    name_pos = self.to_position(var_name, ctx)
                    type = self.type_translator.translate(var_name.type, ctx)
                    qname = mangled.quantifier_var_name(var_name.id)
                    var_decl = self.viper_ast.LocalVarDecl(qname, type, name_pos)
                    quants.append(var_decl)
                    ctx.quantified_vars[var_name.id] = var_decl
                    ctx.all_vars[var_name.id] = var_decl

                # The last argument to forall is the quantified expression
                expr = self._translate_spec(node.args[num_args - 1], ctx)

                # The arguments in the middle are the triggers
                triggers = []
                for arg in node.args[1: num_args - 1]:
                    trigger_pos = self.to_position(arg, ctx)
                    trigger_exprs = [self._translate_spec(t, ctx) for t in arg.elts]
                    trigger = self.viper_ast.Trigger(trigger_exprs, trigger_pos)
                    triggers.append(trigger)

                return [], self.viper_ast.Forall(quants, triggers, expr, pos)
        elif name == names.RESULT:
            var = ctx.result_var
            local_var = self.viper_ast.LocalVar(var.name(), var.typ(), pos)
            return [], local_var
        elif name == names.SUCCESS:
            # The syntax for success is either
            #   - success()
            # or
            #   - success(if_not=expr)
            # where expr can be a disjunction of conditions
            var = ctx.success_var
            local_var = self.viper_ast.LocalVar(var.name(), var.typ(), pos)

            conds = set()

            def collect_conds(node):
                if isinstance(node, ast.Name):
                    conds.add(node.id)
                elif isinstance(node, ast.BoolOp):
                    for val in node.values:
                        collect_conds(val)

            assert len(node.keywords) <= 1
            if node.keywords:
                args = node.keywords[0].value
                collect_conds(args)

            if names.SUCCESS_SENDER_FAILED in conds:
                msg_sender_call_failed = helpers.msg_sender_call_fail_var(self.viper_ast, pos).localVar()
                not_msg_sender_call_failed = self.viper_ast.Not(msg_sender_call_failed, pos)
                return [], self.viper_ast.Implies(not_msg_sender_call_failed, local_var, pos)
            elif names.SUCCESS_OUT_OF_GAS in conds:
                out_of_gas = helpers.out_of_gas_var(self.viper_ast, pos).localVar()
                not_out_of_gas = self.viper_ast.Not(out_of_gas, pos)
                return [], self.viper_ast.Implies(not_out_of_gas, local_var, pos)
            else:
                return [], local_var
        elif name == names.OLD or name == names.ISSUED:
            if len(node.args) != 1:
                # TODO: remove this
                raise InvalidProgramException(node, "Old expression requires a single argument.")

            self_var = ctx.old_self_var if name == names.OLD else ctx.issued_self_var
            with self_scope(self_var, self_var, ctx):
                arg = node.args[0]
                return [], self._translate_spec(arg, ctx)
        elif name == names.SUM:
            # TODO: remove this
            if len(node.args) != 1:
                raise InvalidProgramException(node, "Sum expression requires a single argument.")

            arg = node.args[0]
            expr = self._translate_spec(arg, ctx)
            key_type = self.type_translator.translate(arg.type.key_type, ctx)

            return [], helpers.map_sum(self.viper_ast, expr, key_type, pos)
        elif name == names.SENT or name == names.RECEIVED:
            self_var = ctx.self_var.localVar()

            if name == names.SENT:
                sent_type = ctx.field_types[mangled.SENT_FIELD]
                sent = helpers.struct_get(self.viper_ast, self_var, mangled.SENT_FIELD, sent_type, ctx.self_type, pos)
                if not node.args:
                    return [], sent
                else:
                    arg = self._translate_spec(node.args[0], ctx)
                    get_arg = helpers.map_get(self.viper_ast, sent, arg, self.viper_ast.Int, self.viper_ast.Int, pos)
                    return [], get_arg
            elif name == names.RECEIVED:
                rec_type = ctx.field_types[mangled.RECEIVED_FIELD]
                rec = helpers.struct_get(self.viper_ast, self_var, mangled.RECEIVED_FIELD, rec_type, ctx.self_type, pos)
                if not node.args:
                    return [], rec
                else:
                    arg = self._translate_spec(node.args[0], ctx)
                    # TODO: handle type stuff better
                    get_arg = helpers.map_get(self.viper_ast, rec, arg, self.viper_ast.Int, self.viper_ast.Int, pos)
                    return [], get_arg
        elif name == names.EVENT:
            event = node.args[0]
            event_name = mangled.event_name(event.func.id)
            args = [self._translate_spec(arg, ctx) for arg in event.args]
            full_perm = self.viper_ast.FullPerm(pos)
            one = self.viper_ast.IntLit(1, pos)
            num = self._translate_spec(node.args[1], ctx) if len(node.args) == 2 else one
            perm = self.viper_ast.IntPermMul(num, full_perm, pos)
            pred_acc = self.viper_ast.PredicateAccess(args, event_name, pos)
            current_perm = self.viper_ast.CurrentPerm(pred_acc, pos)
            return [], self.viper_ast.EqCmp(current_perm, perm, pos)
        elif name not in names.NOT_ALLOWED_IN_SPEC:
            return super().translate_Call(node, ctx)
        else:
            # TODO: remove this
            raise InvalidProgramException(node, f"Call to function {name} not allowed in specification.")
