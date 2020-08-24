"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from collections import ChainMap
from contextlib import contextmanager
from functools import reduce
from itertools import chain, starmap, zip_longest
from typing import List, Optional

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.types import VyperType
from twovyper.ast.visitors import NodeVisitor

from twovyper.translation import helpers, mangled
from twovyper.translation.context import Context
from twovyper.translation.allocation import AllocationTranslator
from twovyper.translation.expression import ExpressionTranslator
from twovyper.translation.resource import ResourceTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.utils import switch

from twovyper.verification import rules

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


class SpecificationTranslator(ExpressionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

        self.allocation_translator = AllocationTranslator(viper_ast)
        self.resource_translator = ResourceTranslator(viper_ast)
        self._assume_events = False
        self._translating_check = False
        self._caller_private_condition = None

    @property
    def no_reverts(self):
        return True

    @contextmanager
    def _ignore_accessible_scope(self, ignore: bool):
        self._ignore_accessible = ignore

        yield

        del self._ignore_accessible

    @contextmanager
    def _event_translation_scope(self, assume_events: bool):
        assume = self._assume_events
        self._assume_events = assume_events

        yield

        self._assume_events = assume

    @contextmanager
    def _check_translation_scope(self):
        translating_check = self._translating_check
        self._translating_check = True

        yield

        self._translating_check = translating_check

    def translate_pre_or_postcondition(self, cond: ast.Node, res: List[Stmt], ctx: Context,
                                       assume_events=False) -> Expr:
        with self._event_translation_scope(assume_events):
            expr = self.translate(cond, res, ctx)
            return expr

    def translate_check(self, check: ast.Node, res: List[Stmt], ctx: Context, is_fail=False) -> Expr:
        with self._check_translation_scope():
            expr = self.translate(check, res, ctx)
        if is_fail:
            # We evaluate the check on failure in the old heap because events didn't
            # happen there
            pos = self.to_position(check, ctx)
            return self.viper_ast.Old(expr, pos)
        else:
            return expr

    def translate_invariant(self, inv: ast.Node, res: List[Stmt], ctx: Context, ignore_accessible=False) -> Expr:
        with self._ignore_accessible_scope(ignore_accessible):
            return self.translate(inv, res, ctx)

    def translate_caller_private(self, expr: ast.Expr, ctx: Context) -> (Expr, Expr):
        self._caller_private_condition = self.viper_ast.TrueLit()
        caller_private_expr = self._translate_spec(expr, ctx)
        return self._caller_private_condition, caller_private_expr

    def _translate_spec(self, node: ast.Node, ctx: Context) -> Expr:
        stmts = []
        expr = self.translate(node, stmts, ctx)
        assert not stmts
        return expr

    def _translate_quantified_vars(self, node: ast.Dict, ctx: Context) -> (List[TranslatedVar], List[Expr]):
        quants = []
        type_assumptions = []
        # The first argument to forall is the variable declaration dict
        for var_name in node.keys:
            name_pos = self.to_position(var_name, ctx)
            qname = mangled.quantifier_var_name(var_name.id)
            qvar = TranslatedVar(var_name.id, qname, var_name.type, self.viper_ast, name_pos)
            tassps = self.type_translator.type_assumptions(qvar.local_var(ctx), qvar.type, ctx)
            type_assumptions.extend(tassps)
            quants.append(qvar)

        return quants, type_assumptions

    def translate_FunctionCall(self, node: ast.FunctionCall, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)

        name = node.name
        if name == names.IMPLIES:
            lhs = self.translate(node.args[0], res, ctx)
            rhs = self.translate(node.args[1], res, ctx)
            return self.viper_ast.Implies(lhs, rhs, pos)
        elif name == names.FORALL:
            with ctx.quantified_var_scope():
                num_args = len(node.args)
                assert len(node.args) > 0
                dict_arg = node.args[0]
                assert isinstance(dict_arg, ast.Dict)

                # The first argument to forall is the variable declaration dict
                quants, type_assumptions = self._translate_quantified_vars(dict_arg, ctx)
                # Add the quantified variables to the context
                for var in quants:
                    ctx.quantified_vars[var.name] = var

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
                with ctx.inside_trigger_scope():
                    for arg in node.args[1: num_args - 1]:
                        trigger_pos = self.to_position(arg, ctx)
                        trigger_exprs = [self._translate_spec(t, ctx) for t in arg.elements]
                        trigger = self.viper_ast.Trigger(trigger_exprs, trigger_pos)
                        triggers.append(trigger)

                quant_var_decls = [var.var_decl(ctx) for var in quants]
                return self.viper_ast.Forall(quant_var_decls, triggers, expr, pos)
        elif name == names.RESULT:
            if node.args:
                call = node.args[0]
                assert isinstance(call, ast.ReceiverCall)
                func = ctx.program.functions[call.name]
                viper_result_type = self.type_translator.translate(func.type.return_type, ctx)
                mangled_name = mangled.pure_function_name(call.name)
                pos = self.to_position(call, ctx, rules=rules.PURE_FUNCTION_FAIL, values={'function': func})
                function_args = call.args.copy()
                for (name, _), arg in zip_longest(func.args.items(), call.args):
                    if not arg:
                        function_args.append(func.defaults[name])
                args = [self.translate(arg, res, ctx) for arg in [call.receiver] + function_args]
                func_app = self.viper_ast.FuncApp(mangled_name, args, pos,
                                                  type=helpers.struct_type(self.viper_ast))
                result_func_app = self.viper_ast.FuncApp(mangled.PURE_RESULT, [func_app], pos, type=self.viper_ast.Int)

                domain = mangled.STRUCT_OPS_DOMAIN
                getter = mangled.STRUCT_GET
                type_map = {self.viper_ast.TypeVar(mangled.STRUCT_OPS_VALUE_VAR): viper_result_type}
                return self.viper_ast.DomainFuncApp(getter, [result_func_app], viper_result_type, pos, None,
                                                    domain_name=domain, type_var_map=type_map)
            else:
                return ctx.result_var.local_var(ctx, pos)
        elif name == names.SUCCESS:
            # The syntax for success is either
            #   - success()
            # or
            #   - success(if_not=expr)
            # where expr can be a disjunction of conditions
            success = ctx.success_var.local_var(ctx, pos)

            conds = set()

            def collect_conds(node):
                if isinstance(node, ast.Name):
                    conds.add(node.id)
                elif isinstance(node, ast.BoolOp):
                    collect_conds(node.left)
                    collect_conds(node.right)

            if node.keywords:
                args = node.keywords[0].value
                collect_conds(args)

                def translate_condition(cond):
                    with switch(cond) as case:
                        if case(names.SUCCESS_OVERFLOW):
                            var = helpers.overflow_var(self.viper_ast, pos)
                        elif case(names.SUCCESS_OUT_OF_GAS):
                            var = helpers.out_of_gas_var(self.viper_ast, pos)
                        elif case(names.SUCCESS_SENDER_FAILED):
                            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
                            out_of_gas_expr = helpers.out_of_gas_var(self.viper_ast, pos).localVar()
                            call_failed_expr = helpers.check_call_failed(self.viper_ast, msg_sender, pos)
                            return self.viper_ast.Or(out_of_gas_expr, call_failed_expr, pos)
                        else:
                            assert False

                        return var.localVar()

                or_conds = [translate_condition(c) for c in conds]
                or_op = reduce(lambda l, r: self.viper_ast.Or(l, r, pos), or_conds)
                not_or_op = self.viper_ast.Not(or_op, pos)
                return self.viper_ast.Implies(not_or_op, success, pos)
            elif node.args:
                call = node.args[0]
                assert isinstance(call, ast.ReceiverCall)
                func = ctx.program.functions[call.name]
                mangled_name = mangled.pure_function_name(call.name)
                function_args = call.args.copy()
                for (name, _), arg in zip_longest(func.args.items(), call.args):
                    if not arg:
                        function_args.append(func.defaults[name])
                args = [self.translate(arg, res, ctx) for arg in [call.receiver] + function_args]
                func_app = self.viper_ast.FuncApp(mangled_name, args, pos,
                                                  type=helpers.struct_type(self.viper_ast))
                return self.viper_ast.FuncApp(mangled.PURE_SUCCESS, [func_app], pos, type=self.viper_ast.Bool)
            else:
                return success
        elif name == names.REVERT:
            if node.args:
                call = node.args[0]
                assert isinstance(call, ast.ReceiverCall)
                func = ctx.program.functions[call.name]
                mangled_name = mangled.pure_function_name(call.name)
                function_args = call.args.copy()
                for (name, _), arg in zip_longest(func.args.items(), call.args):
                    if not arg:
                        function_args.append(func.defaults[name])
                args = [self.translate(arg, res, ctx) for arg in [call.receiver] + function_args]
                func_app = self.viper_ast.FuncApp(mangled_name, args, pos,
                                                  type=helpers.struct_type(self.viper_ast))
                success = self.viper_ast.FuncApp(mangled.PURE_SUCCESS, [func_app], pos, type=self.viper_ast.Bool)
            else:
                success = ctx.success_var.local_var(ctx, pos)
            return self.viper_ast.Not(success, pos)
        elif name == names.PREVIOUS:
            arg = node.args[0]
            assert isinstance(arg, ast.Name)
            assert ctx.loop_arrays.get(arg.id)
            assert ctx.loop_indices.get(arg.id)
            array = ctx.loop_arrays[arg.id]
            end = ctx.loop_indices[arg.id].local_var(ctx)
            return self.viper_ast.SeqTake(array, end, pos)
        elif name == names.LOOP_ARRAY:
            arg = node.args[0]
            assert isinstance(arg, ast.Name)
            assert ctx.loop_arrays.get(arg.id)
            return ctx.loop_arrays[arg.id]
        elif name == names.LOOP_ITERATION:
            arg = node.args[0]
            assert isinstance(arg, ast.Name)
            assert ctx.loop_indices.get(arg.id)
            return ctx.loop_indices[arg.id].local_var(ctx)
        elif name == names.OLD or name == names.ISSUED or name == names.PUBLIC_OLD:
            with switch(name) as case:
                if case(names.OLD):
                    self_state = ctx.current_old_state
                elif case(names.PUBLIC_OLD):
                    self_state = ctx.old_state
                elif case(names.ISSUED):
                    self_state = ctx.issued_state
                else:
                    assert False
            with ctx.state_scope(self_state, self_state):
                if name == names.OLD:
                    ctx.locals = ChainMap(ctx.old_locals, ctx.locals)
                arg = node.args[0]
                return self.translate(arg, res, ctx)
        elif name == names.SUM:
            arg = node.args[0]
            expr = self.translate(arg, res, ctx)
            if isinstance(arg.type, types.MapType):
                key_type = self.type_translator.translate(arg.type.key_type, ctx)

                return helpers.map_sum(self.viper_ast, expr, key_type, pos)
            elif isinstance(arg.type, types.ArrayType):
                if isinstance(arg, ast.FunctionCall):
                    if (arg.name == names.RANGE
                            and hasattr(expr, "getArgs")):
                        range_args = expr.getArgs()
                        func_app = self.viper_ast.FuncApp(mangled.RANGE_SUM, [], pos, type=self.viper_ast.Int)
                        return func_app.withArgs(range_args)
                    elif arg.name == names.PREVIOUS:
                        loop_var = arg.args[0]
                        loop_array = ctx.loop_arrays.get(loop_var.id)
                        if (hasattr(loop_array, "funcname")
                                and hasattr(loop_array, "getArgs")
                                and loop_array.funcname() == mangled.RANGE_RANGE):
                            lower_arg = loop_array.getArgs().head()
                            loop_idx = ctx.loop_indices[loop_var.id].local_var(ctx)
                            upper_arg = self.viper_ast.SeqIndex(loop_array, loop_idx, pos)
                            range_args = self.viper_ast.to_seq([lower_arg, upper_arg])
                            func_app = self.viper_ast.FuncApp(mangled.RANGE_SUM, [], pos, type=self.viper_ast.Int)
                            return func_app.withArgs(range_args)

                int_lit_zero = self.viper_ast.IntLit(0, pos)
                sum_value = int_lit_zero
                for i in range(arg.type.size):
                    int_lit_i = self.viper_ast.IntLit(i, pos)
                    array_at = self.viper_ast.SeqIndex(expr, int_lit_i, pos)
                    if arg.type.is_strict:
                        value = array_at
                    else:
                        seq_length = self.viper_ast.SeqLength(expr, pos)
                        cond = self.viper_ast.LtCmp(int_lit_i, seq_length, pos)
                        value = self.viper_ast.CondExp(cond, array_at, int_lit_zero, pos)
                    sum_value = self.viper_ast.Add(sum_value, value, pos)
                return sum_value
            else:
                assert False
        elif name == names.LOCKED:
            lock_name = node.args[0].s
            return helpers.get_lock(self.viper_ast, lock_name, ctx, pos)
        elif name == names.STORAGE:
            args = node.args
            # We translate storage(self) just as the self variable, otherwise we look up
            # the struct in the contract state map
            arg = self.translate(args[0], res, ctx)
            contracts = ctx.current_state[mangled.CONTRACTS].local_var(ctx)
            key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
            value_type = helpers.struct_type(self.viper_ast)
            get_storage = helpers.map_get(self.viper_ast, contracts, arg, key_type, value_type)
            self_address = helpers.self_address(self.viper_ast, pos)
            eq = self.viper_ast.EqCmp(arg, self_address)
            self_var = ctx.self_var.local_var(ctx, pos)
            if ctx.inside_trigger:
                return get_storage
            else:
                return self.viper_ast.CondExp(eq, self_var, get_storage, pos)
        elif name == names.RECEIVED:
            self_var = ctx.self_var.local_var(ctx)
            if node.args:
                arg = self.translate(node.args[0], res, ctx)
                return self.balance_translator.get_received(self_var, arg, ctx, pos)
            else:
                return self.balance_translator.received(self_var, ctx, pos)
        elif name == names.SENT:
            self_var = ctx.self_var.local_var(ctx)
            if node.args:
                arg = self.translate(node.args[0], res, ctx)
                return self.balance_translator.get_sent(self_var, arg, ctx, pos)
            else:
                return self.balance_translator.sent(self_var, ctx, pos)
        elif name == names.INTERPRETED:
            with ctx.interpreted_scope():
                interpreted_arg = self.translate(node.args[0], res, ctx)
                res.append(self.viper_ast.Assert(interpreted_arg, pos))
            uninterpreted_arg = self.translate(node.args[0], res, ctx)
            res.append(self.viper_ast.Inhale(uninterpreted_arg, pos))
            return self.viper_ast.TrueLit(pos)
        elif name == names.CONDITIONAL:
            self._caller_private_condition = self.translate(node.args[0], res, ctx)
            return self.translate(node.args[1], res, ctx)
        elif name == names.ALLOCATED:
            resource = self.resource_translator.translate(node.resource, res, ctx)
            allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx)
            if node.args:
                address = self.translate(node.args[0], res, ctx)
                return self.allocation_translator.get_allocated(allocated, resource, address, ctx)
            else:
                return self.allocation_translator.get_allocated_map(allocated, resource, ctx, pos)
        elif name == names.OFFERED:
            from_resource, to_resource = self.resource_translator.translate_exchange(node.resource, res, ctx)
            offered = ctx.current_state[mangled.OFFERED].local_var(ctx)
            args = [self.translate(arg, res, ctx) for arg in node.args]
            return self.allocation_translator.get_offered(offered, from_resource, to_resource, *args, ctx, pos)
        elif name == names.TRUSTED:
            address = self.translate(node.args[0], res, ctx)
            by = self.translate(node.keywords[0].value, res, ctx)
            trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx)
            return self.allocation_translator.get_trusted(trusted, address, by, ctx, pos)
        elif name == names.ACCESSIBLE:
            # The function necessary for accessible is either the one used as the third argument
            # or the one the heuristics determined
            if len(node.args) == 2:
                func_name = ctx.program.analysis.accessible_function.name
            else:
                func_name = node.args[2].name

            is_wrong_func = ctx.function and func_name != ctx.function.name
            # If we ignore accessibles or if we are in a function not mentioned in the accessible
            # expression we just use True as the body
            # Triggers, however, always need to be translated correctly, because every trigger
            # has to mention all quantified variables
            if (self._ignore_accessible or is_wrong_func) and not ctx.inside_trigger:
                return self.viper_ast.TrueLit(pos)
            else:
                stmts = []

                tag = self.viper_ast.IntLit(ctx.program.analysis.accessible_tags[node], pos)
                to = self.translate(node.args[0], stmts, ctx)
                amount = self.translate(node.args[1], stmts, ctx)
                if len(node.args) == 2:
                    func_args = [amount] if ctx.program.analysis.accessible_function.args else []
                else:
                    args = node.args[2].args
                    func_args = [self.translate(arg, stmts, ctx) for arg in args]

                acc_name = mangled.accessible_name(func_name)
                acc_args = [tag, to, amount, *func_args]
                pred_acc = self.viper_ast.PredicateAccess(acc_args, acc_name, pos)
                # Inside triggers we need to use the predicate access, not the permission amount
                if ctx.inside_trigger:
                    assert not stmts
                    return pred_acc

                res.extend(stmts)
                return self.viper_ast.PredicateAccessPredicate(pred_acc, self.viper_ast.FullPerm(pos), pos)
        elif name == names.INDEPENDENT:
            res = self.translate(node.args[0], res, ctx)

            def unless(node):
                if isinstance(node, ast.FunctionCall):
                    # An old expression
                    with ctx.state_scope(ctx.current_old_state, ctx.current_old_state):
                        return unless(node.args[0])
                elif isinstance(node, ast.Attribute):
                    struct_type = node.value.type
                    stmts = []
                    ref = self.translate(node.value, stmts, ctx)
                    assert not stmts
                    tt = lambda t: self.type_translator.translate(t, ctx)
                    get = lambda m, t: helpers.struct_get(self.viper_ast, ref, m, tt(t), struct_type, pos)
                    members = struct_type.member_types.items()
                    gets = [get(member, member_type) for member, member_type in members if member != node.attr]
                    lows = [self.viper_ast.Low(get, position=pos) for get in gets]
                    return unless(node.value) + lows
                elif isinstance(node, ast.Name):
                    variables = [ctx.old_self_var, ctx.msg_var, ctx.block_var, ctx.chain_var, ctx.tx_var, *ctx.args.values()]
                    return [self.viper_ast.Low(var.local_var(ctx, pos), position=pos) for var in variables if var.name != node.id]

            lows = unless(node.args[1])
            lhs = reduce(lambda v1, v2: self.viper_ast.And(v1, v2, pos), lows)
            rhs = self._low(res, node.args[0].type, ctx, pos)
            return self.viper_ast.Implies(lhs, rhs, pos)
        elif name == names.REORDER_INDEPENDENT:
            arg = self.translate(node.args[0], res, ctx)
            # Using the current msg_var is ok since we don't use msg.gas, but always return fresh values,
            # therefore msg is constant
            variables = [ctx.issued_self_var, ctx.chain_var, ctx.tx_var, ctx.msg_var, *ctx.args.values()]
            low_variables = [self.viper_ast.Low(var.local_var(ctx), position=pos) for var in variables]
            cond = reduce(lambda v1, v2: self.viper_ast.And(v1, v2, pos), low_variables)
            implies = self.viper_ast.Implies(cond, self._low(arg, node.args[0].type, ctx, pos), pos)
            return implies
        elif name == names.EVENT:
            event = node.args[0]
            assert isinstance(event, ast.FunctionCall)
            event_name = mangled.event_name(event.name)
            args = [self.translate(arg, res, ctx) for arg in event.args]
            pred_acc = self.viper_ast.PredicateAccess(args, event_name, pos)
            # If this is a trigger, we just return the predicate access without the surrounding perm-expression and
            # comparison (which is not valid as a trigger).
            if ctx.inside_trigger:
                return pred_acc
            else:
                one = self.viper_ast.IntLit(1, pos)
                num = self.translate(node.args[1], res, ctx) if len(node.args) == 2 else one
                full_perm = self.viper_ast.FullPerm(pos)
                perm_mul = self.viper_ast.IntPermMul(num, full_perm, pos)
                current_perm = self.viper_ast.CurrentPerm(pred_acc, pos)
                eq_comp = self.viper_ast.EqCmp(current_perm, perm_mul, pos)
                if self._translating_check:
                    return eq_comp
                else:
                    cond = self.viper_ast.GtCmp(num, self.viper_ast.IntLit(0, pos), pos)
                    pred_acc_pred = self.viper_ast.PredicateAccessPredicate(pred_acc, perm_mul, pos)
                    if self._assume_events:
                        local_event_args = ctx.event_vars.get(event_name)
                        assert local_event_args
                        assert len(local_event_args) == len(args)
                        args_cond = self.viper_ast.TrueLit(pos)
                        for local_event_arg, event_arg in zip(local_event_args, args):
                            arg_eq = self.viper_ast.NeCmp(local_event_arg, event_arg, pos)
                            args_cond = self.viper_ast.And(args_cond, arg_eq, pos)
                        pred_acc_pred = self.viper_ast.And(args_cond, pred_acc_pred, pos)
                        cond_pred_acc_pred = self.viper_ast.CondExp(cond, pred_acc_pred, args_cond, pos)
                        return cond_pred_acc_pred
                    else:
                        implies = self.viper_ast.Implies(cond, pred_acc_pred, pos)
                        return self.viper_ast.And(eq_comp, implies, pos)
        elif name == names.SELFDESTRUCT:
            self_var = ctx.self_var.local_var(ctx)
            self_type = ctx.self_type
            member = mangled.SELFDESTRUCT_FIELD
            type = self.type_translator.translate(self_type.member_types[member], ctx)
            sget = helpers.struct_get(self.viper_ast, self_var, member, type, self_type, pos)
            return sget
        elif name == names.OVERFLOW:
            return helpers.overflow_var(self.viper_ast, pos).localVar()
        elif name == names.OUT_OF_GAS:
            return helpers.out_of_gas_var(self.viper_ast, pos).localVar()
        elif name == names.FAILED:
            addr = self.translate(node.args[0], res, ctx)
            return helpers.check_call_failed(self.viper_ast, addr, pos)
        elif name == names.IMPLEMENTS:
            if ctx.program.config.has_option(names.CONFIG_TRUST_CASTS):
                return self.viper_ast.TrueLit(pos)
            address = self.translate(node.args[0], res, ctx)
            interface = node.args[1].id
            return helpers.implements(self.viper_ast, address, interface, ctx, pos)
        elif name in ctx.program.ghost_functions:
            function = ctx.program.ghost_functions[name]
            args = [self.translate(arg, res, ctx) for arg in node.args]
            address = args[0]

            contracts = ctx.current_state[mangled.CONTRACTS].local_var(ctx)
            key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
            value_type = helpers.struct_type(self.viper_ast)
            struct = helpers.map_get(self.viper_ast, contracts, address, key_type, value_type)

            # If we are not inside a trigger and the ghost function in question has an
            # implementation, we pass the self struct to it if the argument is the self address,
            # as the verifier does not know that $contracts[self] is equal to the self struct.
            if not ctx.inside_trigger and name in ctx.program.ghost_function_implementations:
                self_address = helpers.self_address(self.viper_ast, pos)
                eq = self.viper_ast.EqCmp(args[0], self_address)
                self_var = ctx.self_var.local_var(ctx, pos)
                struct = self.viper_ast.CondExp(eq, self_var, struct, pos)

            return_type = self.type_translator.translate(function.type.return_type, ctx)

            rpos = self.to_position(node, ctx, rules.PRECONDITION_IMPLEMENTS_INTERFACE)
            return helpers.ghost_function(self.viper_ast, name, address, struct, args[1:], return_type, rpos)
        elif name == names.CALLER:
            return ctx.all_vars[mangled.CALLER].local_var(ctx)
        elif name not in names.NOT_ALLOWED_IN_SPEC:
            return super().translate_FunctionCall(node, res, ctx)
        else:
            assert False

    def translate_ReceiverCall(self, node: ast.ReceiverCall, res: List[Stmt], ctx: Context) -> Expr:
        if node.receiver.id == names.LEMMA:
            return super().translate_ReceiverCall(node, res, ctx)
        assert False

    def _low(self, expr, type: VyperType, ctx: Context, pos=None) -> Expr:
        comp = self.type_translator.comparator(type, ctx)
        if comp:
            return self.viper_ast.Low(expr, *comp, pos)
        else:
            return self.viper_ast.Low(expr, position=pos)

    def _injectivity_check(self, node: ast.Node,
                           qvars: List[TranslatedVar],
                           resource: Optional[ast.Expr],
                           args: List[ast.Expr],
                           amount: Optional[ast.Expr],
                           rule: rules.Rule, res: List[Stmt], ctx: Context):
        # To check injectivity we do the following:
        #   forall q1_1, q1_2, q2_1, q2_2, ... :: q1_1 != q1_2 or q2_1 != q2_2 or ... ==>
        #     arg1(q1_1, q2_1, ...) != arg1(q1_2, q2_2, ...) or arg2(q1_1, q2_1, ...) != arg2(q1_2, q2_2, ...) or ...
        #       or amount(q1_1, q2_1, ...) == 0 or amount(q1_2, q2_2) == 0 or ...
        # i.e. that if any two quantified variables are different, at least one pair of arguments is also different if
        # the amount offered is non-zero.
        assert qvars

        all_args = ([] if resource is None else _ResourceArgumentExtractor().extract_args(resource)) + args

        pos = self.to_position(node, ctx)

        true = self.viper_ast.TrueLit(pos)
        false = self.viper_ast.FalseLit(pos)

        qtvars = [[], []]
        qtlocals = [[], []]
        type_assumptions = [[], []]
        for i in range(2):
            for idx, var in enumerate(qvars):
                new_var = TranslatedVar(var.name, f'$arg{idx}{i}', var.type, self.viper_ast, pos)
                qtvars[i].append(new_var)
                local = new_var.local_var(ctx)
                qtlocals[i].append(local)
                type_assumptions[i].extend(self.type_translator.type_assumptions(local, var.type, ctx))

        tas = reduce(lambda a, b: self.viper_ast.And(a, b, pos), chain(*type_assumptions), true)

        or_op = lambda a, b: self.viper_ast.Or(a, b, pos)
        ne_op = lambda a, b: self.viper_ast.NeCmp(a, b, pos)
        cond = reduce(or_op, starmap(ne_op, zip(*qtlocals)))

        zero = self.viper_ast.IntLit(0, pos)

        targs = [[], []]
        is_zero = []
        for i in range(2):
            with ctx.quantified_var_scope():
                ctx.quantified_vars.update((var.name, var) for var in qtvars[i])
                for arg in all_args:
                    targ = self.translate(arg, res, ctx)
                    targs[i].append(targ)

                if amount:
                    tamount = self.translate(amount, res, ctx)
                    is_zero.append(self.viper_ast.EqCmp(tamount, zero, pos))

        arg_neq = reduce(or_op, starmap(ne_op, zip(*targs)), false)
        if is_zero:
            arg_neq = self.viper_ast.Or(arg_neq, reduce(or_op, is_zero), pos)

        expr = self.viper_ast.Implies(tas, self.viper_ast.Implies(cond, arg_neq, pos), pos)
        quant = self.viper_ast.Forall([var.var_decl(ctx) for var in chain(*qtvars)], [], expr, pos)

        modelt = self.model_translator.save_variables(res, ctx, pos)

        combined_rule = rules.combine(rules.INJECTIVITY_CHECK_FAIL, rule)
        apos = self.to_position(node, ctx, combined_rule, modelt=modelt)
        res.append(self.viper_ast.Assert(quant, apos))

    def translate_ghost_statement(self, node: ast.FunctionCall, res: List[Stmt], ctx: Context, is_performs: bool = False) -> Expr:
        pos = self.to_position(node, ctx)
        name = node.name
        if name == names.REALLOCATE:
            resource = self.resource_translator.translate(node.resource, res, ctx)
            amount = self.translate(node.args[0], res, ctx)

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
            to = None
            frm = msg_sender
            for kw in node.keywords:
                kw_val = self.translate(kw.value, res, ctx)
                if kw.name == names.REALLOCATE_TO:
                    to = kw_val
                elif kw.name == names.REALLOCATE_ACTING_FOR:
                    frm = kw_val
                else:
                    assert False

            if is_performs:
                self.allocation_translator.performs(node, [resource, frm, to, amount], res, ctx, pos)
            else:
                self.allocation_translator.reallocate(node, resource, frm, to, amount, msg_sender, res, ctx, pos)

            return None
        elif name == names.OFFER:
            from_resource, to_resource = self.resource_translator.translate_exchange(node.resource, res, ctx)

            left = self.translate(node.args[0], res, ctx)
            right = self.translate(node.args[1], res, ctx)

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)

            all_args = node.args.copy()
            frm = msg_sender
            for kw in node.keywords:
                kw_val = self.translate(kw.value, res, ctx)
                if kw.name == names.OFFER_TO:
                    to = kw_val
                    all_args.append(kw.value)
                elif kw.name == names.OFFER_ACTING_FOR:
                    frm = kw_val
                elif kw.name == names.OFFER_TIMES:
                    times = kw_val
                    times_arg = kw.value
                else:
                    assert False

            if ctx.quantified_vars:
                rule = rules.OFFER_FAIL
                self._injectivity_check(node, ctx.quantified_vars.values(), node.resource, all_args, times_arg, rule, res, ctx)

            if is_performs:
                self.allocation_translator.performs(node, [from_resource, to_resource, left, right, frm, to, times], res, ctx, pos)
            else:
                self.allocation_translator.offer(node, from_resource, to_resource, left, right, frm, to, times, msg_sender, res, ctx, pos)

            return None
        elif name == names.REVOKE:
            from_resource, to_resource = self.resource_translator.translate_exchange(node.resource, res, ctx)

            left = self.translate(node.args[0], res, ctx)
            right = self.translate(node.args[1], res, ctx)
            to = self.translate(node.keywords[0].value, res, ctx)

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
            all_args = node.args.copy()
            frm = msg_sender
            for kw in node.keywords:
                kw_val = self.translate(kw.value, res, ctx)
                if kw.name == names.REVOKE_TO:
                    to = kw_val
                    all_args.append(kw.value)
                elif kw.name == names.REVOKE_ACTING_FOR:
                    frm = kw_val
                else:
                    assert False

            if ctx.quantified_vars:
                rule = rules.REVOKE_FAIL
                self._injectivity_check(node, ctx.quantified_vars.values(), node.resource, all_args, None, rule, res, ctx)

            if is_performs:
                self.allocation_translator.performs(node, [from_resource, to_resource, left, right, frm, to], res, ctx, pos)
            else:
                self.allocation_translator.revoke(node, from_resource, to_resource, left, right, frm, to, msg_sender, res, ctx, pos)

            return None
        elif name == names.EXCHANGE:
            assert not is_performs

            resource1, resource2 = self.resource_translator.translate_exchange(node.resource, res, ctx)

            left = self.translate(node.args[0], res, ctx)
            right = self.translate(node.args[1], res, ctx)
            left_owner = self.translate(node.args[2], res, ctx)
            right_owner = self.translate(node.args[3], res, ctx)

            times = self.translate(node.keywords[0].value, res, ctx)

            self.allocation_translator.exchange(node, resource1, resource2, left, right, left_owner, right_owner, times, res, ctx, pos)

            return None
        elif name == names.CREATE:
            resource = self.resource_translator.translate(node.resource, res, ctx)
            amount = self.translate(node.args[0], res, ctx)

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
            to = msg_sender
            frm = msg_sender
            args = []

            for kw in node.keywords:
                if kw.name == names.CREATE_TO:
                    to = self.translate(kw.value, res, ctx)
                    args.append(kw.value)
                elif kw.name == names.CREATE_ACTING_FOR:
                    frm = self.translate(kw.value, res, ctx)
                    # The 'by' parameter is not part of the injectivity check as
                    # it does not make a difference as to which resource is created
                else:
                    assert False

            if ctx.quantified_vars:
                rule = rules.CREATE_FAIL
                self._injectivity_check(node, ctx.quantified_vars.values(), node.resource, args, node.args[0], rule, res, ctx)

            if is_performs:
                self.allocation_translator.performs(node, [resource, frm, to, amount], res, ctx, pos)
            else:
                is_init = ctx.function.name == names.INIT
                self.allocation_translator.create(node, resource, frm, to, amount, msg_sender, is_init, res, ctx, pos)

            return None
        elif name == names.DESTROY:
            resource = self.resource_translator.translate(node.resource, res, ctx)
            amount = self.translate(node.args[0], res, ctx)

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
            frm = msg_sender
            for kw in node.keywords:
                kw_val = self.translate(kw.value, res, ctx)
                if kw.name == names.DESTROY_ACTING_FOR:
                    frm = kw_val

            if ctx.quantified_vars:
                rule = rules.DESTROY_FAIL
                self._injectivity_check(node, ctx.quantified_vars.values(), node.resource, [], node.args[0], rule, res, ctx)

            if is_performs:
                self.allocation_translator.performs(node, [resource, frm, amount], res, ctx, pos)
            else:
                self.allocation_translator.destroy(node, resource, frm, amount, msg_sender, res, ctx, pos)

            return None
        elif name == names.TRUST:
            address = self.translate(node.args[0], res, ctx)
            val = self.translate(node.args[1], res, ctx)

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
            frm = msg_sender
            for kw in node.keywords:
                kw_val = self.translate(kw.value, res, ctx)
                if kw.name == names.TRUST_ACTING_FOR:
                    frm = kw_val

            if ctx.quantified_vars:
                rule = rules.TRUST_FAIL
                self._injectivity_check(node, ctx.quantified_vars.values(), None, [node.args[0]], None, rule, res, ctx)

            if is_performs:
                self.allocation_translator.performs(node, [address, frm, val], res, ctx, pos)
            else:
                self.allocation_translator.trust(node, address, frm, val, msg_sender, res, ctx, pos)

            return None
        elif name == names.FOREACH:
            assert len(node.args) > 0
            dict_arg = node.args[0]
            assert isinstance(dict_arg, ast.Dict)
            with ctx.quantified_var_scope():
                quants, _ = self._translate_quantified_vars(dict_arg, ctx)
                for var in quants:
                    ctx.quantified_vars[var.name] = var

                return self.translate_ghost_statement(node.args[1], res, ctx, is_performs)
        else:
            assert False


class _ResourceArgumentExtractor(NodeVisitor):

    def extract_args(self, node: ast.Expr) -> List[ast.Expr]:
        return self.visit(node)

    def visit_Name(self, node: ast.Name) -> List[ast.Expr]:
        return []

    def visit_Exchange(self, node: ast.Exchange) -> List[ast.Expr]:
        return self.visit(node.left) + self.visit(node.right)

    def visit_FunctionCall(self, node: ast.FunctionCall) -> List[ast.Expr]:
        if node.name == names.CREATOR:
            return self.visit(node.args[0])
        else:
            return node.args

    def generic_visit(self, node: ast.Node) -> List[ast.Expr]:
        assert False
