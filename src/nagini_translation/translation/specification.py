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
from nagini_translation.translation.builtins import map_sum

from nagini_translation.translation import builtins

from nagini_translation.exceptions import InvalidProgramException

from nagini_translation.viper.ast import ViperAST
from nagini_translation.viper.typedefs import StmtsAndExpr


class SpecificationTranslator(ExpressionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

    def translate_precondition(self, pre: ast.AST, ctx: Context):
        return self._translate_spec(pre, ctx)

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

    def translate_invariant(self, inv: ast.AST, ctx: Context, is_pre=False, is_init=False, is_issued=False):
        # Invariants do not have to hold before __init__
        if (is_pre or is_issued) and is_init:
            return None

        # If we assume the invariant for the issued state alone we use that as self
        self_var = ctx.issued_self_var if is_issued and is_pre else ctx.self_var
        # If we assume the invariant for a single state or if we are in init, old and self
        # are the same
        if is_pre or is_init:
            old_var = self_var
        # If we use the issued state, that is our old state
        elif is_issued:
            old_var = ctx.issued_self_var
        # Else we use the normal old state
        else:
            old_var = ctx.old_self_var

        with self_scope(self_var, old_var, ctx):
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
                    qname = builtins.quantifier_var_name(var_name.id)
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
            var = ctx.success_var
            local_var = self.viper_ast.LocalVar(var.name(), var.typ(), pos)

            def is_msg_sender(node) -> bool:
                is_attr = lambda n: isinstance(n.operand, ast.Attribute)
                is_sender = lambda n: n.operand.attr == names.MSG_SENDER
                is_msg_sender = lambda n: isinstance(n.operand.value, ast.Name) and n.operand.value.id == names.MSG
                return is_attr(node) and is_sender(node) and is_msg_sender(node)

            if len(node.args) == 1 and is_msg_sender(node.args[0]):
                msg_sender_call_failed = builtins.msg_sender_call_fail_var(self.viper_ast, pos).localVar()
                not_msg_sender_call_failed = self.viper_ast.Not(msg_sender_call_failed, pos)
                return [], self.viper_ast.Implies(not_msg_sender_call_failed, local_var, pos)
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

            return [], map_sum(self.viper_ast, expr, key_type, pos)
        elif name == names.SENT or name == names.RECEIVED:
            self_var = ctx.self_var.localVar()

            if name == names.SENT:
                sent_type = ctx.field_types[builtins.SENT_FIELD]
                sent = builtins.struct_get(self.viper_ast, self_var, builtins.SENT_FIELD, sent_type, ctx.self_type, pos)
                if not node.args:
                    return [], sent
                else:
                    arg = self._translate_spec(node.args[0], ctx)
                    get_arg = builtins.map_get(self.viper_ast, sent, arg, self.viper_ast.Int, self.viper_ast.Int, pos)
                    return [], get_arg
            elif name == names.RECEIVED:
                rec_type = ctx.field_types[builtins.RECEIVED_FIELD]
                rec = builtins.struct_get(self.viper_ast, self_var, builtins.RECEIVED_FIELD, rec_type, ctx.self_type, pos)
                if not node.args:
                    return [], rec
                else:
                    arg = self._translate_spec(node.args[0], ctx)
                    # TODO: handle type stuff better
                    get_arg = builtins.map_get(self.viper_ast, rec, arg, self.viper_ast.Int, self.viper_ast.Int, pos)
                    return [], get_arg
        elif name == names.EVENT:
            event = node.args[0]
            event_name = builtins.event_name(event.func.id)
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
