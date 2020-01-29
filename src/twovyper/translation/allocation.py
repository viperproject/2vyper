"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from functools import reduce
from typing import Callable, List

from twovyper.ast import ast_nodes as ast, names, types

from twovyper.translation import helpers, mangled
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context
from twovyper.translation.model import ModelTranslator
from twovyper.translation.resource import ResourceTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.verification import rules
from twovyper.verification.rules import Rules

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


class AllocationTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

        self.model_translator = ModelTranslator(viper_ast)
        self.resource_translator = ResourceTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    @property
    def specification_translator(self):
        from twovyper.translation.specification import SpecificationTranslator
        return SpecificationTranslator(self.viper_ast)

    def get_allocated_map(self, allocated: Expr, resource: Expr, ctx: Context, pos=None, info=None) -> Expr:
        """
        Returns the allocated map for a resource.
        """
        allocated_type = helpers.allocated_type()
        key_type = self.type_translator.translate(allocated_type.key_type, ctx)
        value_type = self.type_translator.translate(allocated_type.value_type, ctx)
        return helpers.map_get(self.viper_ast, allocated, resource, key_type, value_type, pos)

    def set_allocated_map(self, allocated: Expr, resource: Expr, new_value: Expr, ctx: Context, pos=None) -> Expr:
        allocated_type = helpers.allocated_type()
        key_type = self.type_translator.translate(allocated_type.key_type, ctx)
        value_type = self.type_translator.translate(allocated_type.value_type, ctx)
        return helpers.map_set(self.viper_ast, allocated, resource, new_value, key_type, value_type, pos)

    def get_allocated(self,
                      allocated: Expr, resource: Expr,
                      address: Expr,
                      ctx: Context, pos=None, info=None) -> Expr:
        allocated_type = helpers.allocated_type()
        key_type = self.type_translator.translate(allocated_type.value_type.key_type, ctx)
        value_type = self.type_translator.translate(allocated_type.value_type.value_type, ctx)
        allocated_map = self.get_allocated_map(allocated, resource, ctx, pos)
        return helpers.map_get(self.viper_ast, allocated_map, address, key_type, value_type, pos, info)

    def get_offered_map(self,
                        offered: Expr,
                        from_resource: Expr, to_resource: Expr,
                        ctx: Context, pos=None) -> Expr:
        """
        Returns the offered map for a pair of resources.
        """
        offered_type = helpers.offered_type()

        key1_type = self.type_translator.translate(offered_type.key_type, ctx)
        value1_type = self.type_translator.translate(offered_type.value_type, ctx)
        offered1 = helpers.map_get(self.viper_ast, offered, from_resource, key1_type, value1_type, pos)

        key2_type = self.type_translator.translate(offered_type.value_type.key_type, ctx)
        value2_type = self.type_translator.translate(offered_type.value_type.value_type, ctx)
        return helpers.map_get(self.viper_ast, offered1, to_resource, key2_type, value2_type, pos)

    def set_offered_map(self,
                        offered: Expr,
                        from_resource: Expr, to_resource: Expr,
                        new_value: Expr,
                        ctx: Context, pos=None) -> Expr:
        offered_type = helpers.offered_type()

        outer_key_type = self.type_translator.translate(offered_type.key_type, ctx)
        outer_value_type = self.type_translator.translate(offered_type.value_type, ctx)
        inner_key_type = self.type_translator.translate(offered_type.value_type.key_type, ctx)
        inner_value_type = self.type_translator.translate(offered_type.value_type.value_type, ctx)

        inner_map = helpers.map_get(self.viper_ast, offered, from_resource, outer_key_type, outer_value_type, pos)
        new_inner = helpers.map_set(self.viper_ast, inner_map, to_resource, new_value, inner_key_type, inner_value_type, pos)
        return helpers.map_set(self.viper_ast, offered, from_resource, new_inner, outer_key_type, outer_value_type, pos)

    def get_offered(self,
                    offered: Expr,
                    from_resource: Expr, to_resource: Expr,
                    from_val: Expr, to_val: Expr,
                    from_addr: Expr, to_addr: Expr,
                    ctx: Context, pos=None, info=None) -> Expr:
        offered_type = helpers.offered_type()
        offered_map = self.get_offered_map(offered, from_resource, to_resource, ctx, pos)
        offer = helpers.offer(self.viper_ast, from_val, to_val, from_addr, to_addr, pos)
        key_type = self.type_translator.translate(offered_type.value_type.value_type.key_type, ctx)
        value_type = self.type_translator.translate(offered_type.value_type.value_type.value_type, ctx)
        return helpers.map_get(self.viper_ast, offered_map, offer, key_type, value_type, pos)

    def set_offered(self,
                    offered: Expr,
                    from_resource: Expr, to_resource: Expr,
                    from_val: Expr, to_val: Expr,
                    from_addr: Expr, to_addr: Expr,
                    new_value: Expr,
                    ctx: Context, pos=None) -> Expr:
        offered_type = helpers.offered_type()
        offered_map = self.get_offered_map(offered, from_resource, to_resource, ctx, pos)
        key_type = self.type_translator.translate(offered_type.value_type.value_type.key_type, ctx)
        value_type = self.type_translator.translate(offered_type.value_type.value_type.value_type, ctx)
        offer = helpers.offer(self.viper_ast, from_val, to_val, from_addr, to_addr, pos)
        set_offered = helpers.map_set(self.viper_ast, offered_map, offer, new_value, key_type, value_type, pos)
        return self.set_offered_map(offered, from_resource, to_resource, set_offered, ctx, pos)

    def _check_allocation(self, node: ast.Node,
                          allocated: Expr, resource: Expr,
                          address: Expr, value: Expr,
                          rule: Rules, ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Checks that `address` has at least `amount` of `resource` allocated to them.
        """
        get_alloc = self.get_allocated(allocated, resource, address, ctx, pos)
        cond = self.viper_ast.LeCmp(value, get_alloc, pos)
        stmts, modelt = self.model_translator.save_variables(ctx)
        apos = self.to_position(node, ctx, rule, modelt=modelt)
        stmts.append(self.viper_ast.Assert(cond, apos, info))
        return stmts

    def _check_creator(self, node: ast.Node,
                       allocated: Expr, creator_resource: Expr,
                       address: Expr,
                       ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Checks that `address` is allowed to create a resource by checking that the
        allocated amount of `creator_resource` is positive.
        """
        one = self.viper_ast.IntLit(1, pos)
        rule = rules.CREATE_FAIL
        return self._check_allocation(node, allocated, creator_resource, address, one, rule, ctx, pos)

    def _check_from_agrees(self, node: ast.Node,
                           offered: Expr,
                           from_resource: Expr, to_resource: Expr,
                           from_val: Expr, to_val: Expr,
                           from_addr: Expr, to_addr: Expr,
                           amount: Expr,
                           ctx: Context, pos=None) -> List[Stmt]:
        """
        Checks that `from_addr` offered to exchange `from_val` for `to_val` to `to_addr`.
        """
        stmts, modelt = self.model_translator.save_variables(ctx, pos)
        get_offered = self.get_offered(offered, from_resource, to_resource, from_val, to_val, from_addr, to_addr, ctx, pos)
        cond = self.viper_ast.LeCmp(amount, get_offered, pos)
        apos = self.to_position(node, ctx, rules.EXCHANGE_FAIL_NO_OFFER, modelt=modelt)
        stmts.append(self.viper_ast.Assert(cond, apos))
        return stmts

    def _change_allocation(self,
                           allocated: Expr, resource: Expr,
                           address: Expr,
                           value: Expr, increase: bool,
                           ctx: Context, pos=None, info=None) -> List[Stmt]:
        get_alloc = self.get_allocated(allocated, resource, address, ctx, pos)
        func = self.viper_ast.Add if increase else self.viper_ast.Sub
        new_value = func(get_alloc, value, pos)
        key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
        value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
        alloc_map = self.get_allocated_map(allocated, resource, ctx, pos)
        set_alloc = helpers.map_set(self.viper_ast, alloc_map, address, new_value, key_type, value_type, pos)
        set_alloc_map = self.set_allocated_map(allocated, resource, set_alloc, ctx, pos)
        alloc_assign = self.viper_ast.LocalVarAssign(allocated, set_alloc_map, pos, info)
        return [alloc_assign]

    def _set_offered(self, offered: Expr,
                     from_resource: Expr, to_resource: Expr,
                     from_val: Expr, to_val: Expr,
                     from_addr: Expr, to_addr: Expr,
                     new_value: Expr,
                     ctx: Context, pos=None):
        set_offered = self.set_offered(offered, from_resource, to_resource, from_val, to_val, from_addr, to_addr, new_value, ctx, pos)
        offered_assign = self.viper_ast.LocalVarAssign(offered, set_offered, pos)

        return [offered_assign]

    def _change_offered(self, offered: Expr,
                        from_resource: Expr, to_resource: Expr,
                        from_val: Expr, to_val: Expr,
                        from_addr: Expr, to_addr: Expr,
                        amount: Expr, increase: bool,
                        ctx: Context, pos=None) -> List[Stmt]:
        get_offered = self.get_offered(offered, from_resource, to_resource, from_val, to_val, from_addr, to_addr, ctx, pos)
        func = self.viper_ast.Add if increase else self.viper_ast.Sub
        new_value = func(get_offered, amount, pos)

        return self._set_offered(offered, from_resource, to_resource, from_val, to_val, from_addr, to_addr, new_value, ctx, pos)

    def _inhale_offers(self,
                       from_val: Expr, to_val: Expr,
                       from_addr: Expr, to_addr: Expr,
                       amount: Expr,
                       ctx: Context, pos=None) -> Stmt:
        type_assumptions = []
        quant_decls = []
        for quant in ctx.quantified_vars.values():
            type_assumptions.extend(self.type_translator.type_assumptions(quant.local_var(ctx, pos), quant.type, ctx))
            quant_decls.append(quant.var_decl(ctx))

        cond = reduce(lambda a, b: self.viper_ast.And(a, b, pos), type_assumptions, self.viper_ast.TrueLit(pos))
        offer = helpers.offer_predicate(self.viper_ast, from_val, to_val, from_addr, to_addr, pos)
        perm = self.viper_ast.IntPermMul(amount, self.viper_ast.FullPerm(pos), pos)
        acc_offer = self.viper_ast.PredicateAccessPredicate(offer, perm, pos)
        trigger = self.viper_ast.Trigger([offer], pos)
        quant = self.viper_ast.Forall(quant_decls, [trigger], self.viper_ast.Implies(cond, acc_offer, pos), pos)
        # TODO: rule
        return self.viper_ast.Inhale(quant, pos)

    def _exhale_offers(self, ctx: Context, pos=None) -> Stmt:
        # We clean up the heap by exhaling all permissions to offer.
        #   exhale forall a, b, c, d: Int :: perm(offer(a, b, c, d)) > none ==> acc(offer(a, b, c, d), perm(offer(a, b, c, d)))
        # We use an implication with a '> none' because of a bug in Carbon (TODO: issue #171) where it isn't possible
        # to exhale no permissions under a quantifier.
        qvars = [self.viper_ast.LocalVarDecl(f'$arg{i}', self.viper_ast.Int, pos) for i in range(4)]
        qvars_locals = [var.localVar() for var in qvars]
        offer = helpers.offer_predicate(self.viper_ast, *qvars_locals, pos)
        perm = self.viper_ast.CurrentPerm(offer, pos)
        cond = self.viper_ast.GtCmp(perm, self.viper_ast.NoPerm(pos), pos)
        acc_offer = self.viper_ast.PredicateAccessPredicate(offer, perm, pos)
        trigger = self.viper_ast.Trigger([offer], pos)
        quant = self.viper_ast.Forall(qvars, [trigger], self.viper_ast.Implies(cond, acc_offer, pos), pos)
        # TODO: rule
        return self.viper_ast.Exhale(quant, pos)

    def allocate(self,
                 allocated: Expr, resource: Expr,
                 address: Expr, amount: Expr,
                 ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Adds `amount` allocation to the allocation map entry of `address`.
        """
        return self._change_allocation(allocated, resource, address, amount, True, ctx, pos, info)

    def reallocate(self, node: ast.Node,
                   allocated: Expr, resource: Expr,
                   frm: Expr, to: Expr, amount: Expr,
                   ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Checks that `from` has sufficient allocation and then moves `amount` allocation from `frm` to `to`.
        """
        check_allocation = self._check_allocation(node, allocated, resource, frm, amount, rules.REALLOCATE_FAIL, ctx, pos, info)
        decs = self._change_allocation(allocated, resource, frm, amount, False, ctx, pos)
        incs = self._change_allocation(allocated, resource, to, amount, True, ctx, pos)
        return check_allocation + decs + incs

    def deallocate(self, node: ast.Node,
                   allocated: Expr, resource: Expr,
                   address: Expr, amount: Expr,
                   ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Checks that `address` has sufficient allocation and then removes `amount` allocation from the allocation map entry of `address`.
        """
        check_allocation = self._check_allocation(node, allocated, resource, address, amount, rules.REALLOCATE_FAIL, ctx, pos, info)
        decs = self._change_allocation(allocated, resource, address, amount, False, ctx, pos, info)
        return check_allocation + decs

    def create(self, node: ast.Node,
               allocated: Expr, resource: Expr,
               to: Expr, amount: Expr,
               is_init: bool,
               ctx: Context, pos=None) -> List[Stmt]:
        if is_init:
            # The initializer is allowed to create all resources unchecked.
            check_creator = []
        else:
            creator_resource = self.resource_translator.creator_resource(resource, ctx, pos)
            check_creator = self._check_creator(node, allocated, creator_resource, to, ctx, pos)
        allocate = self.allocate(allocated, resource, to, amount, ctx, pos)
        return check_creator + allocate

    def _leak_check(self, node: ast.Node, rule: Rules, ctx: Context, pos=None, info=None) -> List[Stmt]:
        """
        Checks that the invariant knows about all ether allocated to the individual addresses, i.e., that
        given only the invariant and the state it is known for each address how much of the ether is
        allocated to them.
        """

        # To do a leak check we create a fresh allocation map, assume the invariants for the current state and
        # the fresh map and then check that the fresh map only specified from the invariants is equal to the
        # actual map. This ensures that the invariant fully specifies the allocation map.

        spec_translator = self.specification_translator

        allocated = ctx.current_state[mangled.ALLOCATED]
        new_allocated_name = ctx.new_local_var_name(mangled.ALLOCATED)
        fresh_allocated = TranslatedVar(mangled.ALLOCATED, new_allocated_name, allocated.type, self.viper_ast, pos)
        ctx.new_local_vars.append(fresh_allocated.var_decl(ctx))
        fresh_allocated_var = fresh_allocated.local_var(ctx, pos)

        stmts = []

        # Assume type assumptions for fresh_allocated
        allocated_ass = self.type_translator.type_assumptions(fresh_allocated_var, fresh_allocated.type, ctx)
        allocated_assumptions = [self.viper_ast.Inhale(c) for c in allocated_ass]
        allocated_info_msg = "Assume type assumptions for fresh allocated"
        stmts.extend(self.seqn_with_info(allocated_assumptions, allocated_info_msg))

        with ctx.allocated_scope(fresh_allocated):
            # We assume the invariant with the current state as the old state because the current allocation
            # should be known from the current state, not the old state. For example, the invariant
            #   allocated() == old(allocated())
            # should be illegal.
            with ctx.state_scope(ctx.current_state, ctx.current_state):
                for inv in ctx.unchecked_invariants():
                    stmts.append(self.viper_ast.Inhale(inv))

                # As an optimization we only assume invariants that mention allocated(), all other invariants
                # are already known since we only changed the allocation map to a fresh one
                for inv in ctx.program.analysis.allocated_invariants:
                    ppos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                    inv_stmts, expr = spec_translator.translate_invariant(inv, ctx, True)
                    stmts.extend(inv_stmts)
                    stmts.append(self.viper_ast.Inhale(expr, ppos))

        model_stmts, modelt = self.model_translator.save_variables(ctx)
        stmts.extend(model_stmts)

        # We create the following check for each resource r:
        #   forall a: address, arg0, arg1, ... :: <type_assumptions> ==>
        #      allocated[r(arg0, arg1, ...)](a) == fresh_allocated[r(arg0, arg1, ...)](a)
        address = self.viper_ast.LocalVarDecl('$a', self.viper_ast.Int, pos)
        address_var = address.localVar()
        address_assumptions = self.type_translator.type_assumptions(address_var, types.VYPER_ADDRESS, ctx)

        for resource in ctx.program.resources.values():
            type_assumptions = address_assumptions.copy()
            args = []
            for idx, arg_type in enumerate(resource.type.member_types.values()):
                type = self.type_translator.translate(arg_type, ctx)
                arg = self.viper_ast.LocalVarDecl(f'$arg{idx}', type, pos)
                args.append(arg)
                arg_var = arg.localVar()
                type_assumptions.extend(self.type_translator.type_assumptions(arg_var, arg_type, ctx))

            cond = reduce(lambda l, r: self.viper_ast.And(l, r, pos), type_assumptions)

            res = self.resource_translator.resource(resource.name, [arg.localVar() for arg in args], ctx)
            allocated_get = self.get_allocated(allocated.local_var(ctx, pos), res, address_var, ctx, pos)
            fresh_allocated_get = self.get_allocated(fresh_allocated_var, res, address_var, ctx, pos)
            allocated_eq = self.viper_ast.EqCmp(allocated_get, fresh_allocated_get, pos)
            trigger = self.viper_ast.Trigger([allocated_get, fresh_allocated_get], pos)
            assertion = self.viper_ast.Forall([address, *args], [trigger], self.viper_ast.Implies(cond, allocated_eq, pos), pos)
            if ctx.function.name == names.INIT:
                # Leak check only has to hold if __init__ succeeds
                succ = ctx.success_var.local_var(ctx, pos)
                assertion = self.viper_ast.Implies(succ, assertion, pos)

            apos = self.to_position(node, ctx, rule, modelt=modelt, values={'resource': resource})
            stmts.append(self.viper_ast.Assert(assertion, apos, info))

        return stmts

    def function_leak_check(self, ctx: Context, pos=None, info=None) -> List[Stmt]:
        return self._leak_check(ctx.function.node or ctx.program.node, rules.ALLOCATION_LEAK_CHECK_FAIL, ctx, pos, info)

    def send_leak_check(self, node: ast.Node, ctx: Context, pos=None, info=None) -> List[Stmt]:
        return self._leak_check(node, rules.CALL_LEAK_CHECK_FAIL, ctx, pos, info)

    def _foreach_change_offer(self, offered: Expr,
                              from_resource: Expr, to_resource: Expr,
                              from_value: Expr, to_value: Expr,
                              from_owner: Expr, to_owner: Expr,
                              times: Expr, op: Callable[[Expr, Expr, Expr], Expr],
                              ctx: Context, pos=None) -> List[Stmt]:
        inhale = self._inhale_offers(from_value, to_value, from_owner, to_owner, times, ctx, pos)

        # Declare the new offered
        offered_map_type = helpers.offered_type().value_type.value_type
        offered_map_type_t = self.type_translator.translate(offered_map_type, ctx)
        key_type_t = self.type_translator.translate(offered_map_type.key_type, ctx)
        value_type_t = self.type_translator.translate(offered_map_type.value_type, ctx)
        fresh_offered_map_name = ctx.new_local_var_name('$offered_map')
        fresh_offered_map = self.viper_ast.LocalVarDecl(fresh_offered_map_name, offered_map_type_t, pos)
        ctx.new_local_vars.append(fresh_offered_map)
        fresh_offered_map_var = fresh_offered_map.localVar()

        # Assume the values of the new map
        offer_type = helpers.offer_type()
        qvars = []
        type_assumptions = []
        for idx, type in enumerate(offer_type.member_types.values()):
            var = self.viper_ast.LocalVarDecl(f'$arg{idx}', self.type_translator.translate(type, ctx), pos)
            qvars.append(var)
            type_assumptions.extend(self.type_translator.type_assumptions(var.localVar(), type, ctx))

        qlocals = [var.localVar() for var in qvars]
        cond = reduce(lambda a, b: self.viper_ast.And(a, b, pos), type_assumptions, self.viper_ast.TrueLit(pos))
        offer = helpers.offer(self.viper_ast, *qlocals, pos)
        fresh_offered_get = helpers.map_get(self.viper_ast, fresh_offered_map_var, offer, key_type_t, value_type_t, pos)
        old_offered_get = self.get_offered(offered, from_resource, to_resource, *qlocals, ctx, pos)
        offer_pred = helpers.offer_predicate(self.viper_ast, *qlocals, pos)
        perm = self.viper_ast.CurrentPerm(offer_pred, pos)
        expr = op(fresh_offered_get, old_offered_get, perm)
        trigger = self.viper_ast.Trigger([fresh_offered_get], pos)
        quant = self.viper_ast.Forall(qvars, [trigger], self.viper_ast.Implies(cond, expr, pos), pos)
        assume = self.viper_ast.Inhale(quant, pos)

        # Set the new offered map entry for [from_resource <-> to_resource]
        set_offered = self.set_offered_map(offered, from_resource, to_resource, fresh_offered_map_var, ctx, pos)
        offered_assign = self.viper_ast.LocalVarAssign(offered, set_offered, pos)

        # Heap clean-up
        exhale = self._exhale_offers(ctx, pos)
        return [inhale, assume, offered_assign, exhale]

    def offer(self, offered: Expr,
              from_resource: Expr, to_resource: Expr,
              from_value: Expr, to_value: Expr,
              from_owner: Expr, to_owner: Expr,
              times: Expr,
              ctx: Context, pos=None) -> List[Stmt]:
        if ctx.quantified_vars:
            # We are translating a
            #   foreach({x1: t1, x2: t2, ...}, offer(e1(x1, x2, ...), e2(x1, x2, ...), to=e3(x1, x2, ...), times=t))
            # To do that, we first inhale the offer predicate
            #   inhale forall x1: t1, x2: t2, ... :: acc(offer(e1(...), e2(...), ..., e3(...)), t * write)
            # to get an injectivity check. For all offers we inhaled some permission to we then set the 'times'
            # entries in a new map to the sum of the old map entries and the current permissions to the respective
            # offer.
            # assume forall $i, $j, $a, $b: Int ::
            #    fresh_offered[{$i, $j, $a, $b}] * write == old_offered[...] * write + perm(offer($i, $j, $a, $b))

            def op(fresh: Expr, old: Expr, perm: Expr) -> Expr:
                write = self.viper_ast.FullPerm(pos)
                fresh_mul = self.viper_ast.IntPermMul(fresh, write, pos)
                old_mul = self.viper_ast.IntPermMul(old, write, pos)
                perm_add = self.viper_ast.PermAdd(old_mul, perm, pos)
                return self.viper_ast.EqCmp(fresh_mul, perm_add, pos)

            stmts = self._foreach_change_offer(offered, from_resource, to_resource, from_value, to_value, from_owner, to_owner, times, op, ctx, pos)
        else:
            stmts = self._change_offered(offered, from_resource, to_resource, from_value, to_value, from_owner, to_owner, times, True, ctx, pos)

        return self.seqn_with_info(stmts, "Offer")

    def revoke(self, offered: Expr,
               from_resource: Expr, to_resource: Expr,
               from_value: Expr, to_value: Expr,
               from_owner: Expr, to_owner: Expr,
               ctx: Context, pos=None) -> List[Stmt]:
        if ctx.quantified_vars:
            # We are translating a
            #   foreach({x1: t1, x2: t2, ...}, revoke(e1(x1, x2, ...), e2(x1, x2, ...), to=e3(x1, x2, ...)))
            # To do that, we first inhale the offer predicate
            #   inhale forall x1: t1, x2: t2, ... :: offer(e1(...), e2(...), ..., e3(...))
            # to get an injectivity check. For all offers we inhaled some permission to we then set the 'times'
            # entries to zero in a new map, all others stay the same.
            # assume forall $i, $j, $a, $b: Int ::
            #    fresh_offered[{$i, $j, $a, $b}] == perm(offer($i, $j, $a, $b)) > none ? 0 : old_offered[...]
            one = self.viper_ast.IntLit(1, pos)

            def op(fresh: Expr, old: Expr, perm: Expr) -> Expr:
                gez = self.viper_ast.GtCmp(perm, self.viper_ast.NoPerm(pos), pos)
                cond_expr = self.viper_ast.CondExp(gez, self.viper_ast.IntLit(0, pos), old, pos)
                return self.viper_ast.EqCmp(fresh, cond_expr, pos)

            stmts = self._foreach_change_offer(offered, from_resource, to_resource, from_value, to_value, from_owner, to_owner, one, op, ctx, pos)
        else:
            zero = self.viper_ast.IntLit(0, pos)
            stmts = self._set_offered(offered, from_resource, to_resource, from_value, to_value, from_owner, to_owner, zero, ctx, pos)

        return self.seqn_with_info(stmts, "Revoke")

    def exchange(self,
                 node: ast.Node,
                 allocated: Expr, offered: Expr,
                 resource1: Expr, resource2: Expr,
                 value1: Expr, value2: Expr,
                 owner1: Expr, owner2: Expr,
                 times: Expr,
                 ctx: Context,
                 pos=None, info=None) -> List[Stmt]:
        zero = self.viper_ast.IntLit(0, pos)
        # If value1 == 0, owner1 will definitely agree, else we check that they offered the exchange, and decrease
        # the offer map by the amount of exchanges we do
        allowed1 = self._check_from_agrees(node, offered, resource1, resource2, value1, value2, owner1, owner2, times, ctx, pos)
        dec_offered1 = self._change_offered(offered, resource1, resource2, value1, value2, owner1, owner2, times, False, ctx, pos)
        is_not_zero1 = self.viper_ast.NeCmp(value1, zero)
        ex1 = self.viper_ast.If(is_not_zero1, [*allowed1, *dec_offered1], [], pos)

        # We do the same for owner2
        allowed2 = self._check_from_agrees(node, offered, resource2, resource1, value2, value1, owner2, owner1, times, ctx, pos)
        dec_offered2 = self._change_offered(offered, resource2, resource1, value2, value1, owner2, owner1, times, False, ctx, pos)
        is_not_zero2 = self.viper_ast.NeCmp(value2, zero)
        ex2 = self.viper_ast.If(is_not_zero2, [*allowed2, *dec_offered2], [], pos)

        amount1 = self.viper_ast.Mul(times, value1)
        check1 = self._check_allocation(node, allocated, resource1, owner1, amount1, rules.EXCHANGE_FAIL_INSUFFICIENT_FUNDS, ctx, pos)

        amount2 = self.viper_ast.Mul(times, value2)
        check2 = self._check_allocation(node, allocated, resource2, owner2, amount2, rules.EXCHANGE_FAIL_INSUFFICIENT_FUNDS, ctx, pos)

        # owner1 gives up amount1 of resource1
        dec1 = self._change_allocation(allocated, resource1, owner1, amount1, False, ctx, pos)
        # owner1 gets amount2 of resource2
        inc1 = self._change_allocation(allocated, resource2, owner1, amount2, True, ctx, pos)

        # owner2 gives up amount2 of resource2
        dec2 = self._change_allocation(allocated, resource2, owner2, amount2, False, ctx, pos)
        # owner2 gets amount1 of resource1
        inc2 = self._change_allocation(allocated, resource1, owner2, amount1, True, ctx, pos)

        return [ex1, ex2, *check1, *check2, *dec1, *inc1, *dec2, *inc2]
