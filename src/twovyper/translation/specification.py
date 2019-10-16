"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from functools import reduce

from twovyper.ast import names

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import StmtsAndExpr

from twovyper.translation.expression import ExpressionTranslator
from twovyper.translation.context import (
    Context, quantified_var_scope, self_scope, inside_trigger_scope
)

from twovyper.translation import mangled
from twovyper.translation import helpers


class SpecificationTranslator(ExpressionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

    def translate_postcondition(self, post: ast.AST, ctx: Context, is_init=False):
        # For postconditions the old state is the state before the function call, except for
        # __init__ where we use the self state instead (since there is no pre-state)
        old_var = ctx.self_var if is_init else ctx.pre_self_var
        with self_scope(ctx.self_var, old_var, ctx):
            return self._translate_spec(post, ctx)

    def translate_check(self, check: ast.AST, ctx: Context, is_fail=False):
        expr = self._translate_spec(check, ctx)
        if is_fail:
            # We evaluate the check on failure in the old heap because events didn't
            # happen there
            pos = self.to_position(check, ctx)
            return self.viper_ast.Old(expr, pos)
        else:
            return expr

    def translate_invariant(self, inv: ast.AST, ctx: Context, ignore_accessible=False):
        self._ignore_accessible = ignore_accessible
        expr = self._translate_spec(inv, ctx)
        del self._ignore_accessible
        return expr

    def _translate_spec(self, node, ctx: Context):
        _, expr = self.translate(node, ctx)
        return expr

    def translate_Call(self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        name = node.func.id
        if name == names.IMPLIES:
            lhs = self._translate_spec(node.args[0], ctx)
            rhs = self._translate_spec(node.args[1], ctx)
            return [], self.viper_ast.Implies(lhs, rhs, pos)
        elif name == names.FORALL:
            with quantified_var_scope(ctx):
                num_args = len(node.args)
                quants = []
                type_assumptions = []
                # The first argument to forall is the variable declaration dict
                for var_name in node.args[0].keys:
                    name_pos = self.to_position(var_name, ctx)
                    type = self.type_translator.translate(var_name.type, ctx)
                    qname = mangled.quantifier_var_name(var_name.id)
                    var_decl = self.viper_ast.LocalVarDecl(qname, type, name_pos)
                    var = var_decl.localVar()
                    tassps = self.type_translator.type_assumptions(var, var_name.type, ctx)
                    type_assumptions.extend(tassps)
                    quants.append(var_decl)
                    ctx.quantified_vars[var_name.id] = var_decl
                    ctx.all_vars[var_name.id] = var_decl

                # The last argument to forall is the quantified expression
                expr = self._translate_spec(node.args[num_args - 1], ctx)

                # We need to assume the type assumptions for the quantified variables
                def chain(assumptions):
                    assumption, *rest = assumptions
                    if rest:
                        return self.viper_ast.And(assumption, chain(rest), pos)
                    else:
                        return assumption

                if type_assumptions:
                    assumption_exprs = chain(type_assumptions)
                    expr = self.viper_ast.Implies(assumption_exprs, expr, pos)

                # The arguments in the middle are the triggers
                triggers = []
                with inside_trigger_scope(ctx):
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
            self_var = ctx.old_self_var if name == names.OLD else ctx.issued_self_var
            with self_scope(self_var, self_var, ctx):
                arg = node.args[0]
                return [], self._translate_spec(arg, ctx)
        elif name == names.SUM:
            arg = node.args[0]
            expr = self._translate_spec(arg, ctx)
            key_type = self.type_translator.translate(arg.type.key_type, ctx)

            return [], helpers.map_sum(self.viper_ast, expr, key_type, pos)
        elif name == names.RECEIVED:
            self_var = ctx.self_var.localVar()
            if node.args:
                arg = self._translate_spec(node.args[0], ctx)
                return [], self.balance_translator.get_received(self_var, arg, ctx, pos)
            else:
                return [], self.balance_translator.received(self_var, ctx, pos)
        elif name == names.SENT:
            self_var = ctx.self_var.localVar()
            if node.args:
                arg = self._translate_spec(node.args[0], ctx)
                return [], self.balance_translator.get_sent(self_var, arg, ctx, pos)
            else:
                return [], self.balance_translator.sent(self_var, ctx, pos)
        elif name == names.ACCESSIBLE:
            # The function ment in accessible is either the one used as the third argument
            # or the one the heuristics determined
            if len(node.args) == 2:
                func_name = ctx.program.analysis.accessible_function.name
            else:
                func_name = node.args[2].func.attr

            is_wrong_func = ctx.function and func_name != ctx.function.name
            # If we ignore accessibles or if we are in a function not mentioned in the accessible
            # expression we just use True as the body
            # Triggers, however, always have to be translated correctly, because every trigger
            # needs to mention all quantified variables
            if (self._ignore_accessible or is_wrong_func) and not ctx.inside_trigger:
                return [], self.viper_ast.TrueLit(pos)
            else:
                tag = self.viper_ast.IntLit(ctx.program.analysis.accessible_tags[node], pos)
                to = self._translate_spec(node.args[0], ctx)
                amount = self._translate_spec(node.args[1], ctx)
                if len(node.args) == 2:
                    func_args = [amount] if ctx.program.analysis.accessible_function.args else []
                else:
                    func_args = [self._translate_spec(arg, ctx) for arg in node.args[2].args]
                acc_name = mangled.accessible_name(func_name)
                acc_args = [tag, to, amount, *func_args]
                pred_acc = self.viper_ast.PredicateAccess(acc_args, acc_name, pos)
                # Inside triggers we need to use the predicate access, not the permission amount
                if ctx.inside_trigger:
                    return [], pred_acc
                full_perm = self.viper_ast.FullPerm(pos)
                return [], self.viper_ast.PredicateAccessPredicate(pred_acc, full_perm, pos)
        elif name == names.REORDER_INDEPENDENT:
            arg = self._translate_spec(node.args[0], ctx)
            # Using the current msg_var is only ok if we don't support gas, i.e. if msg is constant
            variables = [ctx.issued_self_var, ctx.msg_var, *ctx.args.values()]
            low_variables = [self.viper_ast.Low(var.localVar()) for var in variables]
            cond = reduce(lambda v1, v2: self.viper_ast.And(v1, v2, pos), low_variables)
            implies = self.viper_ast.Implies(cond, self.viper_ast.Low(arg, pos), pos)
            return [], implies
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
        elif name == names.SELFDESTRUCT:
            self_var = ctx.self_var.localVar()
            self_type = ctx.self_type
            member = mangled.SELFDESTRUCT_FIELD
            type = self.type_translator.translate(self_type.member_types[member], ctx)
            sget = helpers.struct_get(self.viper_ast, self_var, member, type, self_type, pos)
            return [], sget
        elif name not in names.NOT_ALLOWED_IN_SPEC:
            return super().translate_Call(node, ctx)
        else:
            assert False
