"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import contextmanager
from functools import reduce
from itertools import chain, starmap
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
from twovyper.viper.typedefs import Expr, Stmt, StmtsAndExpr


class SpecificationTranslator(ExpressionTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

        self.allocation_translator = AllocationTranslator(viper_ast)
        self.resource_translator = ResourceTranslator(viper_ast)

    @property
    def no_reverts(self):
        return True

    @contextmanager
    def _ignore_accessible_scope(self, ignore: bool):
        self._ignore_accessible = ignore

        yield

        del self._ignore_accessible

    def translate_postcondition(self, post: ast.Node, ctx: Context):
        return self.translate(post, ctx)

    def translate_check(self, check: ast.Node, ctx: Context, is_fail=False):
        stmts, expr = self.translate(check, ctx)
        if is_fail:
            # We evaluate the check on failure in the old heap because events didn't
            # happen there
            pos = self.to_position(check, ctx)
            return stmts, self.viper_ast.Old(expr, pos)
        else:
            return stmts, expr

    def translate_invariant(self, inv: ast.Node, ctx: Context, ignore_accessible=False):
        with self._ignore_accessible_scope(ignore_accessible):
            return self.translate(inv, ctx)

    def _translate_spec(self, node: ast.Node, ctx: Context):
        stmts, expr = self.translate(node, ctx)
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

    def translate_FunctionCall(self, node: ast.FunctionCall, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)

        name = node.name
        if name == names.IMPLIES:
            lhs_stmts, lhs = self.translate(node.args[0], ctx)
            rhs_stmts, rhs = self.translate(node.args[1], ctx)
            return lhs_stmts + rhs_stmts, self.viper_ast.Implies(lhs, rhs, pos)
        elif name == names.FORALL:
            with ctx.quantified_var_scope():
                num_args = len(node.args)

                # The first argument to forall is the variable declaration dict
                quants, type_assumptions = self._translate_quantified_vars(node.args[0], ctx)
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
                return [], self.viper_ast.Forall(quant_var_decls, triggers, expr, pos)
        elif name == names.RESULT:
            return [], ctx.result_var.local_var(ctx, pos)
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
                            return helpers.check_call_failed(self.viper_ast, msg_sender, pos)
                        else:
                            assert False

                        return var.localVar()

                or_conds = [translate_condition(c) for c in conds]
                or_op = reduce(lambda l, r: self.viper_ast.Or(l, r, pos), or_conds)
                not_or_op = self.viper_ast.Not(or_op, pos)
                return [], self.viper_ast.Implies(not_or_op, success, pos)
            else:
                return [], success
        elif name == names.REVERT:
            success = ctx.success_var.local_var(ctx, pos)
            return [], self.viper_ast.Not(success, pos)
        elif name == names.OLD or name == names.ISSUED:
            self_state = ctx.current_old_state if name == names.OLD else ctx.issued_state
            with ctx.state_scope(self_state, self_state):
                arg = node.args[0]
                return self.translate(arg, ctx)
        elif name == names.SUM:
            arg = node.args[0]
            stmts, expr = self.translate(arg, ctx)
            key_type = self.type_translator.translate(arg.type.key_type, ctx)

            return stmts, helpers.map_sum(self.viper_ast, expr, key_type, pos)
        elif name == names.LOCKED:
            lock_name = node.args[0].s
            return [], helpers.get_lock(self.viper_ast, lock_name, ctx, pos)
        elif name == names.STORAGE:
            args = node.args
            # We translate storage(self) just as the self variable, otherwise we look up
            # the struct in the contract state map
            stmts, arg = self.translate(args[0], ctx)
            contracts = ctx.current_state[mangled.CONTRACTS].local_var(ctx)
            key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
            value_type = helpers.struct_type(self.viper_ast)
            get_storage = helpers.map_get(self.viper_ast, contracts, arg, key_type, value_type)
            self_address = helpers.self_address(self.viper_ast, pos)
            eq = self.viper_ast.EqCmp(arg, self_address)
            self_var = ctx.self_var.local_var(ctx, pos)
            if ctx.inside_trigger:
                return stmts, get_storage
            else:
                return stmts, self.viper_ast.CondExp(eq, self_var, get_storage, pos)
        elif name == names.RECEIVED:
            self_var = ctx.self_var.local_var(ctx)
            if node.args:
                stmts, arg = self.translate(node.args[0], ctx)
                return stmts, self.balance_translator.get_received(self_var, arg, ctx, pos)
            else:
                return [], self.balance_translator.received(self_var, ctx, pos)
        elif name == names.SENT:
            self_var = ctx.self_var.local_var(ctx)
            if node.args:
                stmts, arg = self.translate(node.args[0], ctx)
                return stmts, self.balance_translator.get_sent(self_var, arg, ctx, pos)
            else:
                return [], self.balance_translator.sent(self_var, ctx, pos)
        elif name == names.ALLOCATED:
            resource_stmts, resource = self.resource_translator.translate(node.resource, ctx)
            allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx)
            if node.args:
                address_stmts, address = self.translate(node.args[0], ctx)
                return resource_stmts + address_stmts, self.allocation_translator.get_allocated(allocated, resource, address, ctx)
            else:
                return resource_stmts, self.allocation_translator.get_allocated_map(allocated, resource, ctx, pos)
        elif name == names.OFFERED:
            resource_stmts, from_resource, to_resource = self.resource_translator.translate_exchange(node.resource, ctx)
            offered = ctx.current_state[mangled.OFFERED].local_var(ctx)
            args_stmts, args = self.collect(self.translate(arg, ctx) for arg in node.args)
            return resource_stmts + args_stmts, self.allocation_translator.get_offered(offered, from_resource, to_resource, *args, ctx, pos)
        elif name == names.TRUSTED:
            address_stmts, address = self.translate(node.args[0], ctx)
            by_stmts, by = self.translate(node.keywords[0].value, ctx)
            trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx)
            return address_stmts + by_stmts, self.allocation_translator.get_trusted(trusted, address, by, ctx, pos)
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
                return [], self.viper_ast.TrueLit(pos)
            else:
                tag = self.viper_ast.IntLit(ctx.program.analysis.accessible_tags[node], pos)
                to_stmts, to = self.translate(node.args[0], ctx)
                amount_stmts, amount = self.translate(node.args[1], ctx)
                stmts = to_stmts + amount_stmts
                if len(node.args) == 2:
                    func_args = [amount] if ctx.program.analysis.accessible_function.args else []
                else:
                    args = node.args[2].args
                    func_stmts, func_args = self.collect(self.translate(arg, ctx) for arg in args)
                    stmts.extend(func_stmts)
                acc_name = mangled.accessible_name(func_name)
                acc_args = [tag, to, amount, *func_args]
                pred_acc = self.viper_ast.PredicateAccess(acc_args, acc_name, pos)
                # Inside triggers we need to use the predicate access, not the permission amount
                if ctx.inside_trigger:
                    assert not stmts
                    return [], pred_acc
                full_perm = self.viper_ast.FullPerm(pos)
                return stmts, self.viper_ast.PredicateAccessPredicate(pred_acc, full_perm, pos)
        elif name == names.INDEPENDENT:
            stmts, res = self.translate(node.args[0], ctx)

            def unless(node):
                if isinstance(node, ast.FunctionCall):
                    # An old expression
                    with ctx.state_scope(ctx.current_old_state, ctx.current_old_state):
                        return unless(node.args[0])
                elif isinstance(node, ast.Attribute):
                    struct_type = node.value.type
                    stmts, ref = self.translate(node.value, ctx)
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
            return stmts, self.viper_ast.Implies(lhs, rhs, pos)
        elif name == names.REORDER_INDEPENDENT:
            stmts, arg = self.translate(node.args[0], ctx)
            # Using the current msg_var is ok since we don't use msg.gas, but always return fresh values,
            # therefore msg is constant
            variables = [ctx.issued_self_var, ctx.chain_var, ctx.tx_var, ctx.msg_var, *ctx.args.values()]
            low_variables = [self.viper_ast.Low(var.local_var(ctx), position=pos) for var in variables]
            cond = reduce(lambda v1, v2: self.viper_ast.And(v1, v2, pos), low_variables)
            implies = self.viper_ast.Implies(cond, self._low(arg, node.args[0].type, ctx, pos), pos)
            return stmts, implies
        elif name == names.EVENT:
            event = node.args[0]
            event_name = mangled.event_name(event.name)
            stmts, args = self.collect(self.translate(arg, ctx) for arg in event.args)
            full_perm = self.viper_ast.FullPerm(pos)
            one = self.viper_ast.IntLit(1, pos)
            num_stmts, num = self.translate(node.args[1], ctx) if len(node.args) == 2 else ([], one)
            stmts.extend(num_stmts)
            pred_acc = self.viper_ast.PredicateAccess(args, event_name, pos)
            # If this is a trigger, we just return the predicate access without the surrounding perm-expression and
            # comparison (which is not valid as a trigger).
            if ctx.inside_trigger:
                return stmts, pred_acc
            perm = self.viper_ast.IntPermMul(num, full_perm, pos)
            current_perm = self.viper_ast.CurrentPerm(pred_acc, pos)
            return stmts, self.viper_ast.EqCmp(current_perm, perm, pos)
        elif name == names.SELFDESTRUCT:
            self_var = ctx.self_var.local_var(ctx)
            self_type = ctx.self_type
            member = mangled.SELFDESTRUCT_FIELD
            type = self.type_translator.translate(self_type.member_types[member], ctx)
            sget = helpers.struct_get(self.viper_ast, self_var, member, type, self_type, pos)
            return [], sget
        elif name == names.OVERFLOW:
            return [], helpers.overflow_var(self.viper_ast, pos).localVar()
        elif name == names.OUT_OF_GAS:
            return [], helpers.out_of_gas_var(self.viper_ast, pos).localVar()
        elif name == names.FAILED:
            stmts, addr = self.translate(node.args[0], ctx)
            return stmts, helpers.check_call_failed(self.viper_ast, addr, pos)
        elif name == names.IMPLEMENTS:
            stmts, address = self.translate(node.args[0], ctx)
            interface = node.args[1].id
            return stmts, helpers.implements(self.viper_ast, address, interface, ctx, pos)
        elif name in ctx.program.ghost_functions:
            function = ctx.program.ghost_functions[name]
            stmts, args = self.collect(self.translate(arg, ctx) for arg in node.args)
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
            return stmts, helpers.ghost_function(self.viper_ast, name, address, struct, args[1:], return_type, rpos)
        elif name not in names.NOT_ALLOWED_IN_SPEC:
            return super().translate_FunctionCall(node, ctx)
        else:
            assert False

    def translate_ReceiverCall(self, node: ast.ReceiverCall, ctx: Context) -> StmtsAndExpr:
        assert False

    def _low(self, expr, type: VyperType, ctx: Context, pos=None, info=None):
        comp = self.type_translator.comparator(type, ctx)
        if comp:
            return self.viper_ast.Low(expr, *comp, pos, info)
        else:
            return self.viper_ast.Low(expr, position=pos, info=info)

    def _injectivity_check(self, node: ast.Node,
                           qvars: List[TranslatedVar],
                           resource: Optional[ast.Expr],
                           args: List[ast.Expr],
                           amount: Optional[ast.Expr],
                           rule: rules.Rules, ctx: Context) -> List[Stmt]:
        # To check injectivity we do the following:
        #   forall q1_1, q1_2, q2_1, q2_2, ... :: q1_1 != q1_2 or q2_1 != q2_2 or ... ==>
        #     arg1(q1_1, q2_1, ...) != arg1(q1_2, q2_2, ...) or arg2(q1_1, q2_1, ...) != arg2(q1_2, q2_2, ...) or ...
        #       or amount(q1_1, q2_1, ...) == 0 or amount(q1_2, q2_2) == 0 or ...
        # i.e. that if any two quantified variables are different, at least one pair of arguments is also different if
        # the amount offered is non-zero.
        assert qvars

        all_args = [] if resource is None else _ResourceArgumentExtractor().extract_args(resource) + args

        pos = self.to_position(node, ctx)
        stmts = []

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
                    arg_stmts, targ = self.translate(arg, ctx)
                    stmts.extend(arg_stmts)
                    targs[i].append(targ)

                if amount:
                    amount_stmts, tamount = self.translate(amount, ctx)
                    stmts.extend(amount_stmts)
                    is_zero.append(self.viper_ast.EqCmp(tamount, zero, pos))

        arg_neq = reduce(or_op, starmap(ne_op, zip(*targs)), false)
        if is_zero:
            arg_neq = self.viper_ast.Or(arg_neq, reduce(or_op, is_zero))

        expr = self.viper_ast.Implies(tas, self.viper_ast.Implies(cond, arg_neq, pos), pos)
        quant = self.viper_ast.Forall([var.var_decl(ctx) for var in chain(*qtvars)], [], expr, pos)

        model_stmts, modelt = self.model_translator.save_variables(ctx, pos)
        stmts.extend(model_stmts)

        apos = self.to_position(node, ctx, rule, modelt=modelt)
        stmts.append(self.viper_ast.Assert(quant, apos))
        return stmts

    def translate_ghost_statement(self, node: ast.FunctionCall, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)
        name = node.name
        if name == names.REALLOCATE:
            stmts, resource = self.resource_translator.translate(node.resource, ctx)
            allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx, pos)

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
            amount_stmts, amount = self.translate(node.args[0], ctx)
            stmts.extend(amount_stmts)
            to_stmts, to = self.translate(node.keywords[0].value, ctx)
            stmts.extend(to_stmts)
            stmts.extend(self.allocation_translator.reallocate(node, allocated, resource, msg_sender, to, amount, ctx, pos))

            return stmts, None
        elif name == names.OFFER:
            resource_stmts, from_resource, to_resource = self.resource_translator.translate_exchange(node.resource, ctx)

            offered = ctx.current_state[mangled.OFFERED].local_var(ctx, pos)

            value1_stmts, value1 = self.translate(node.args[0], ctx)
            value2_stmts, value2 = self.translate(node.args[1], ctx)

            stmts = [*resource_stmts, *value1_stmts, *value2_stmts]
            all_args = node.args.copy()
            for kw in node.keywords:
                if kw.name == names.OFFER_TO:
                    to_stmts, to = self.translate(kw.value, ctx)
                    stmts.extend(to_stmts)
                    all_args.append(kw.value)
                elif kw.name == names.OFFER_TIMES:
                    times_stmts, times = self.translate(kw.value, ctx)
                    stmts.extend(times_stmts)
                    times_arg = kw.value

            if ctx.quantified_vars:
                rule = rules.OFFER_INJECTIVITY_CHECK_FAIL
                stmts.extend(self._injectivity_check(node, ctx.quantified_vars.values(), node.resource, all_args, times_arg, rule, ctx))

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
            stmts.extend(self.allocation_translator.offer(offered, from_resource, to_resource, value1, value2, msg_sender, to, times, ctx, pos))
            return stmts, None
        elif name == names.REVOKE:
            resource_stmts, from_resource, to_resource = self.resource_translator.translate_exchange(node.resource, ctx)

            offered = ctx.current_state[mangled.OFFERED].local_var(ctx, pos)

            value1_stmts, value1 = self.translate(node.args[0], ctx)
            value2_stmts, value2 = self.translate(node.args[1], ctx)
            to_stmts, to = self.translate(node.keywords[0].value, ctx)

            stmts = [*resource_stmts, *value1_stmts, *value2_stmts, *to_stmts]

            if ctx.quantified_vars:
                all_args = [*node.args, node.keywords[0].value]
                rule = rules.REVOKE_INJECTIVITY_CHECK_FAIL
                stmts.extend(self._injectivity_check(node, ctx.quantified_vars.values(), node.resource, all_args, None, rule, ctx))

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
            stmts.extend(self.allocation_translator.revoke(offered, from_resource, to_resource, value1, value2, msg_sender, to, ctx, pos))
            return stmts, None
        elif name == names.EXCHANGE:
            resource_stmts, resource1, resource2 = self.resource_translator.translate_exchange(node.resource, ctx)

            value1_stmts, value1 = self.translate(node.args[0], ctx)
            value2_stmts, value2 = self.translate(node.args[1], ctx)
            owner1_stmts, owner1 = self.translate(node.args[2], ctx)
            owner2_stmts, owner2 = self.translate(node.args[3], ctx)

            times_stmts, times = self.translate(node.keywords[0].value, ctx)

            allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx, pos)
            offered = ctx.current_state[mangled.OFFERED].local_var(ctx, pos)
            exchange = self.allocation_translator.exchange
            exchange_stmts = exchange(node, allocated, offered, resource1, resource2, value1, value2, owner1, owner2, times, ctx, pos)

            return [*resource_stmts, *value1_stmts, *value2_stmts, *owner1_stmts, *owner2_stmts, *times_stmts, *exchange_stmts], None
        elif name == names.CREATE:
            resource_stmts, resource = self.resource_translator.translate(node.resource, ctx)
            amount_stmts, amount = self.translate(node.args[0], ctx)

            msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
            to_stmts, to = [], msg_sender
            args = []

            for kw in node.keywords:
                if kw.name == names.CREATE_TO:
                    to_stmts, to = self.translate(kw.value, ctx)
                    args.append(kw.value)

            if ctx.quantified_vars:
                rule = rules.CREATE_INJECTIVITY_CHECK_FAIL
                injectivity_stmts = self._injectivity_check(node, ctx.quantified_vars.values(), node.resource, args, node.args[0], rule, ctx)
            else:
                injectivity_stmts = []

            allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx, pos)
            is_init = ctx.function.name == names.INIT
            allocation_stmts = self.allocation_translator.create(node, allocated, resource, msg_sender, to, amount, is_init, ctx, pos)

            return resource_stmts + amount_stmts + to_stmts + injectivity_stmts + allocation_stmts, None
        elif name == names.DESTROY:
            resource_stmts, resource = self.resource_translator.translate(node.resource, ctx)
            amount_stmts, amount = self.translate(node.args[0], ctx)
            to = helpers.msg_sender(self.viper_ast, ctx, pos)

            if ctx.quantified_vars:
                rule = rules.DESTROY_INJECTIVITY_CHECK_FAIL
                injectivity_stmts = self._injectivity_check(node, ctx.quantified_vars.values(), node.resource, [], node.args[0], rule, ctx)
            else:
                injectivity_stmts = []

            allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx, pos)
            deallocation_stmts = self.allocation_translator.destroy(node, allocated, resource, to, amount, ctx, pos)

            return resource_stmts + amount_stmts + injectivity_stmts + deallocation_stmts, None
        elif name == names.TRUST:
            address_stmts, address = self.translate(node.args[0], ctx)
            val_stmts, val = self.translate(node.args[1], ctx)
            by = helpers.msg_sender(self.viper_ast, ctx, pos)
            trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx)
            trust_stmts = self.allocation_translator.trust(trusted, address, by, val, ctx, pos)
            return address_stmts + val_stmts + trust_stmts, None
        elif name == names.FOREACH:
            with ctx.quantified_var_scope():
                quants, _ = self._translate_quantified_vars(node.args[0], ctx)
                for var in quants:
                    ctx.quantified_vars[var.name] = var

                return self.translate_ghost_statement(node.args[1], ctx)
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
