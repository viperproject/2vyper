"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from functools import reduce
from typing import Callable, List, Union

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.nodes import VyperProgram

from twovyper.translation import helpers, mangled
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.context import Context
from twovyper.translation.model import ModelTranslator
from twovyper.translation.resource import ResourceTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.verification import rules
from twovyper.verification.rules import Rule

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt, Trigger


class AllocationTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

        self.model_translator = ModelTranslator(viper_ast)
        self.resource_translator = ResourceTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    @property
    def specification_translator(self):
        from twovyper.translation.specification import SpecificationTranslator
        return SpecificationTranslator(self.viper_ast)

    def _quantifier(self, expr: Expr, _: List[Trigger], ctx: Context, pos=None) -> Expr:
        type_assumptions = []
        qvars = []
        for var in ctx.quantified_vars.values():
            type_assumptions.extend(self.type_translator.type_assumptions(var.local_var(ctx, pos), var.type, ctx))
            qvars.append(var.var_decl(ctx))

        cond = reduce(lambda a, b: self.viper_ast.And(a, b, pos), type_assumptions, self.viper_ast.TrueLit(pos))
        # TODO: select good triggers
        return self.viper_ast.Forall(qvars, [], self.viper_ast.Implies(cond, expr, pos), pos)

    def get_allocated_map(self, allocated: Expr, resource: Expr, ctx: Context, pos=None) -> Expr:
        """
        Returns the allocated map for a resource.
        """
        allocated_type = helpers.allocated_type()
        key_type = self.type_translator.translate(allocated_type.key_type, ctx)
        value_type = self.type_translator.translate(allocated_type.value_type, ctx)
        map_get = helpers.map_get(self.viper_ast, allocated, resource, key_type, value_type, pos)
        return map_get

    def set_allocated_map(self, allocated: Expr, resource: Expr, new_value: Expr, ctx: Context, pos=None) -> Expr:
        allocated_type = helpers.allocated_type()
        key_type = self.type_translator.translate(allocated_type.key_type, ctx)
        value_type = self.type_translator.translate(allocated_type.value_type, ctx)
        return helpers.map_set(self.viper_ast, allocated, resource, new_value, key_type, value_type, pos)

    def get_allocated(self,
                      allocated: Expr, resource: Expr,
                      address: Expr,
                      ctx: Context, pos=None) -> Expr:
        allocated_type = helpers.allocated_type()
        key_type = self.type_translator.translate(allocated_type.value_type.key_type, ctx)
        value_type = self.type_translator.translate(allocated_type.value_type.value_type, ctx)
        allocated_map = self.get_allocated_map(allocated, resource, ctx, pos)
        map_get = helpers.map_get(self.viper_ast, allocated_map, address, key_type, value_type, pos)
        return map_get

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
        map_get = helpers.map_get(self.viper_ast, offered1, to_resource, key2_type, value2_type, pos)
        return map_get

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
        new_inner = helpers.map_set(self.viper_ast, inner_map, to_resource, new_value,
                                    inner_key_type, inner_value_type, pos)
        return helpers.map_set(self.viper_ast, offered, from_resource, new_inner, outer_key_type, outer_value_type, pos)

    def get_offered(self,
                    offered: Expr,
                    from_resource: Expr, to_resource: Expr,
                    from_val: Expr, to_val: Expr,
                    from_addr: Expr, to_addr: Expr,
                    ctx: Context, pos=None) -> Expr:
        offered_type = helpers.offered_type()
        offered_map = self.get_offered_map(offered, from_resource, to_resource, ctx, pos)
        offer = helpers.offer(self.viper_ast, from_val, to_val, from_addr, to_addr, pos)
        key_type = self.type_translator.translate(offered_type.value_type.value_type.key_type, ctx)
        value_type = self.type_translator.translate(offered_type.value_type.value_type.value_type, ctx)
        map_get = helpers.map_get(self.viper_ast, offered_map, offer, key_type, value_type, pos)
        return map_get

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

    def get_trusted_map(self, trusted: Expr, where: Expr, ctx: Context, pos=None):
        trusted_type = helpers.trusted_type()

        key_type = self.type_translator.translate(trusted_type.key_type, ctx)
        value_type = self.type_translator.translate(trusted_type.value_type, ctx)
        return helpers.map_get(self.viper_ast, trusted, where, key_type, value_type, pos)

    def get_trusted(self,
                    trusted: Expr, where: Expr,
                    address: Expr, by_address: Expr,
                    ctx: Context, pos=None) -> Expr:
        """
        Returns the trusted map for a pair of addresses.
        """
        trusted_type = helpers.trusted_type()

        key1_type = self.type_translator.translate(trusted_type.key_type, ctx)
        value1_type = self.type_translator.translate(trusted_type.value_type, ctx)
        trusted1 = helpers.map_get(self.viper_ast, trusted, where, key1_type, value1_type, pos)

        key2_type = self.type_translator.translate(trusted_type.value_type.key_type, ctx)
        value2_type = self.type_translator.translate(trusted_type.value_type.value_type, ctx)
        trusted2 = helpers.map_get(self.viper_ast, trusted1, address, key2_type, value2_type, pos)

        key3_type = self.type_translator.translate(trusted_type.value_type.value_type.key_type, ctx)
        value3_type = self.type_translator.translate(trusted_type.value_type.value_type.value_type, ctx)
        map_get = helpers.map_get(self.viper_ast, trusted2, by_address, key3_type, value3_type, pos)
        return map_get

    def set_trusted(self,
                    trusted: Expr, where: Expr,
                    address: Expr, by_address: Expr,
                    new_value: Expr,
                    ctx: Context, pos=None) -> Expr:
        trusted_type = helpers.trusted_type()

        key1_type = self.type_translator.translate(trusted_type.key_type, ctx)
        value1_type = self.type_translator.translate(trusted_type.value_type, ctx)
        middle_map = helpers.map_get(self.viper_ast, trusted, where, key1_type, value1_type, pos)

        key2_type = self.type_translator.translate(trusted_type.value_type.key_type, ctx)
        value2_type = self.type_translator.translate(trusted_type.value_type.value_type, ctx)
        inner_map = helpers.map_get(self.viper_ast, middle_map, address, key2_type, value2_type, pos)

        key3_type = self.type_translator.translate(trusted_type.value_type.value_type.key_type, ctx)
        value3_type = self.type_translator.translate(trusted_type.value_type.value_type.value_type, ctx)

        new_inner = helpers.map_set(self.viper_ast, inner_map, by_address, new_value, key3_type, value3_type, pos)
        new_middle = helpers.map_set(self.viper_ast, middle_map, address, new_inner, key2_type, value2_type, pos)
        return helpers.map_set(self.viper_ast, trusted, where, new_middle, key1_type, value1_type, pos)

    def _check_allocation(self, node: ast.Node,
                          resource: Expr, address: Expr, value: Expr,
                          rule: Rule, res: List[Stmt], ctx: Context, pos=None):
        """
        Checks that `address` has at least `amount` of `resource` allocated to them.
        """
        if ctx.inside_interface_call:
            return

        allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx, pos)
        get_alloc = self.get_allocated(allocated, resource, address, ctx, pos)
        cond = self.viper_ast.LeCmp(value, get_alloc, pos)
        if ctx.quantified_vars:
            trigger = self.viper_ast.Trigger([get_alloc], pos)
            cond = self._quantifier(cond, [trigger], ctx, pos)

        modelt = self.model_translator.save_variables(res, ctx, pos)
        apos = self.to_position(node, ctx, rule, modelt=modelt)
        res.append(self.viper_ast.Assert(cond, apos))

    def _check_creator(self, node: ast.Node,
                       creator_resource: Expr,
                       address: Expr, amount: Expr,
                       res: List[Stmt], ctx: Context, pos=None):
        """
        Checks that `address` is allowed to create `amount` resources by checking that the
        allocated amount of `creator_resource` is positive if `amount` > 0
        """
        zero = self.viper_ast.IntLit(0, pos)
        one = self.viper_ast.IntLit(1, pos)
        gtz = self.viper_ast.GtCmp(amount, zero, pos)
        cond = self.viper_ast.CondExp(gtz, one, zero, pos)
        rule = rules.CREATE_FAIL_NOT_A_CREATOR
        self._check_allocation(node, creator_resource, address, cond, rule, res, ctx, pos)

    def _check_from_agrees(self, node: ast.Node,
                           from_resource: Expr, to_resource: Expr,
                           from_val: Expr, to_val: Expr,
                           from_addr: Expr, to_addr: Expr,
                           amount: Expr,
                           res: List[Stmt], ctx: Context, pos=None):
        """
        Checks that `from_addr` offered to exchange `from_val` for `to_val` to `to_addr`.
        """
        if ctx.inside_interface_call:
            return

        offered = ctx.current_state[mangled.OFFERED].local_var(ctx, pos)
        modelt = self.model_translator.save_variables(res, ctx, pos)
        get_offered = self.get_offered(offered, from_resource, to_resource, from_val, to_val,
                                       from_addr, to_addr, ctx, pos)
        cond = self.viper_ast.LeCmp(amount, get_offered, pos)
        apos = self.to_position(node, ctx, rules.EXCHANGE_FAIL_NO_OFFER, modelt=modelt)
        res.append(self.viper_ast.Assert(cond, apos))

    def _change_allocation(self,
                           resource: Expr, address: Expr,
                           value: Expr, increase: bool,
                           res: List[Stmt], ctx: Context, pos=None):
        allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx, pos)
        get_alloc = self.get_allocated(allocated, resource, address, ctx, pos)
        func = self.viper_ast.Add if increase else self.viper_ast.Sub
        new_value = func(get_alloc, value, pos)
        key_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
        value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
        alloc_map = self.get_allocated_map(allocated, resource, ctx, pos)
        set_alloc = helpers.map_set(self.viper_ast, alloc_map, address, new_value, key_type, value_type, pos)
        set_alloc_map = self.set_allocated_map(allocated, resource, set_alloc, ctx, pos)
        alloc_assign = self.viper_ast.LocalVarAssign(allocated, set_alloc_map, pos)
        res.append(alloc_assign)

    def _foreach_change_allocation(self,
                                   resource: Expr, address: Expr, amount: Expr,
                                   op: Callable[[Expr, Expr, Expr], Expr],
                                   res: List[Stmt], ctx: Context, pos=None):
        allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx, pos)

        self._inhale_allocation(resource, address, amount, res, ctx, pos)

        allocated_type = self.type_translator.translate(helpers.allocated_type(), ctx)
        fresh_allocated_name = ctx.new_local_var_name(names.ALLOCATED)
        fresh_allocated_decl = self.viper_ast.LocalVarDecl(fresh_allocated_name, allocated_type, pos)
        ctx.new_local_vars.append(fresh_allocated_decl)
        fresh_allocated = fresh_allocated_decl.localVar()

        # Assume the values of the new map
        qaddr = self.viper_ast.LocalVarDecl('$a', self.viper_ast.Int, pos)
        qaddr_var = qaddr.localVar()
        qres = self.viper_ast.LocalVarDecl('$r', helpers.struct_type(self.viper_ast), pos)
        qres_var = qres.localVar()

        fresh_allocated_get = self.get_allocated(fresh_allocated, qres_var, qaddr_var, ctx, pos)
        old_allocated_get = self.get_allocated(allocated, qres_var, qaddr_var, ctx, pos)
        allocation_pred = helpers.allocation_predicate(self.viper_ast, qres_var, qaddr_var, pos)
        perm = self.viper_ast.CurrentPerm(allocation_pred, pos)
        expr = op(fresh_allocated_get, old_allocated_get, perm)
        trigger = self.viper_ast.Trigger([fresh_allocated_get], pos)
        quant = self.viper_ast.Forall([qaddr, qres], [trigger], expr, pos)
        assume = self.viper_ast.Inhale(quant, pos)
        res.append(assume)

        # Set the new allocated
        allocated_assign = self.viper_ast.LocalVarAssign(allocated, fresh_allocated, pos)
        res.append(allocated_assign)

        # Heap clean-up
        self._exhale_allocation(res, ctx, pos)

    def _inhale_allocation(self,
                           resource: Expr,
                           address: Expr, amount: Expr,
                           res: List[Stmt], ctx: Context, pos=None):
        allocation = helpers.allocation_predicate(self.viper_ast, resource, address, pos)
        perm = self.viper_ast.IntPermMul(amount, self.viper_ast.FullPerm(pos), pos)
        acc_allocation = self.viper_ast.PredicateAccessPredicate(allocation, perm, pos)
        trigger = self.viper_ast.Trigger([allocation], pos)
        quant = self._quantifier(acc_allocation, [trigger], ctx, pos)
        # TODO: rule
        res.append(self.viper_ast.Inhale(quant, pos))

    def _exhale_allocation(self, res: List[Stmt], _: Context, pos=None):
        # We use an implication with a '> none' because of a bug in Carbon (TODO: issue #171) where it isn't possible
        # to exhale no permissions under a quantifier.
        qres = self.viper_ast.LocalVarDecl('$r', helpers.struct_type(self.viper_ast), pos)
        qaddr = self.viper_ast.LocalVarDecl('$a', self.viper_ast.Int, pos)
        allocation = helpers.allocation_predicate(self.viper_ast, qres.localVar(), qaddr.localVar(), pos)
        perm = self.viper_ast.CurrentPerm(allocation, pos)
        cond = self.viper_ast.GtCmp(perm, self.viper_ast.NoPerm(pos), pos)
        acc_allocation = self.viper_ast.PredicateAccessPredicate(allocation, perm, pos)
        trigger = self.viper_ast.Trigger([allocation], pos)
        quant = self.viper_ast.Forall([qres, qaddr], [trigger], self.viper_ast.Implies(cond, acc_allocation, pos), pos)
        # TODO: rule
        res.append(self.viper_ast.Exhale(quant, pos))

    def _exhale_trust(self, res: List[Stmt], _: Context, pos=None):
        # We use an implication with a '> none' because of a bug in Carbon (TODO: issue #171) where it isn't possible
        # to exhale no permissions under a quantifier.
        qwhere = self.viper_ast.LocalVarDecl('$where', self.viper_ast.Int, pos)
        qwhom = self.viper_ast.LocalVarDecl('$whom', self.viper_ast.Int, pos)
        qwho = self.viper_ast.LocalVarDecl('$who', self.viper_ast.Int, pos)
        trust = helpers.trust_predicate(self.viper_ast, qwhere.localVar(), qwhom.localVar(), qwho.localVar(), pos)
        perm = self.viper_ast.CurrentPerm(trust, pos)
        cond = self.viper_ast.GtCmp(perm, self.viper_ast.NoPerm(pos), pos)
        acc_allocation = self.viper_ast.PredicateAccessPredicate(trust, perm, pos)
        trigger = self.viper_ast.Trigger([trust], pos)
        quant = self.viper_ast.Forall([qwhere, qwhom, qwho], [trigger],
                                      self.viper_ast.Implies(cond, acc_allocation, pos), pos)
        # TODO: rule
        res.append(self.viper_ast.Exhale(quant, pos))

    def _set_offered(self,
                     from_resource: Expr, to_resource: Expr,
                     from_val: Expr, to_val: Expr,
                     from_addr: Expr, to_addr: Expr,
                     new_value: Expr,
                     res: List[Stmt], ctx: Context, pos=None):
        offered = ctx.current_state[mangled.OFFERED].local_var(ctx, pos)
        set_offered = self.set_offered(offered, from_resource, to_resource, from_val, to_val, from_addr,
                                       to_addr, new_value, ctx, pos)
        offered_assign = self.viper_ast.LocalVarAssign(offered, set_offered, pos)
        res.append(offered_assign)

    def _change_offered(self,
                        from_resource: Expr, to_resource: Expr,
                        from_val: Expr, to_val: Expr,
                        from_addr: Expr, to_addr: Expr,
                        amount: Expr, increase: bool,
                        res: List[Stmt], ctx: Context, pos=None):
        offered = ctx.current_state[mangled.OFFERED].local_var(ctx, pos)
        get_offered = self.get_offered(offered, from_resource, to_resource, from_val,
                                       to_val, from_addr, to_addr, ctx, pos)
        func = self.viper_ast.Add if increase else self.viper_ast.Sub
        new_value = func(get_offered, amount, pos)

        self._set_offered(from_resource, to_resource, from_val, to_val, from_addr, to_addr, new_value, res, ctx, pos)

    def _foreach_change_offered(self,
                                from_resource: Expr, to_resource: Expr,
                                from_value: Expr, to_value: Expr,
                                from_owner: Expr, to_owner: Expr,
                                times: Expr, op: Callable[[Expr, Expr, Expr], Expr],
                                res: List[Stmt], ctx: Context, pos=None):
        offered = ctx.current_state[mangled.OFFERED].local_var(ctx, pos)

        self._inhale_offers(from_resource, to_resource, from_value, to_value, from_owner,
                            to_owner, times, res, ctx, pos)

        # Declare the new offered
        offered_type = self.type_translator.translate(helpers.offered_type(), ctx)
        fresh_offered_name = ctx.new_local_var_name(names.OFFERED)
        fresh_offered_decl = self.viper_ast.LocalVarDecl(fresh_offered_name, offered_type, pos)
        ctx.new_local_vars.append(fresh_offered_decl)
        fresh_offered = fresh_offered_decl.localVar()

        # Assume the values of the new map
        qvar_types = 2 * [helpers.struct_type(self.viper_ast)] + 4 * [self.viper_ast.Int]
        qvars = [self.viper_ast.LocalVarDecl(f'$arg{i}', t, pos) for i, t in enumerate(qvar_types)]
        qlocals = [var.localVar() for var in qvars]

        fresh_offered_get = self.get_offered(fresh_offered, *qlocals, ctx, pos)
        old_offered_get = self.get_offered(offered, *qlocals, ctx, pos)
        offer_pred = helpers.offer_predicate(self.viper_ast, *qlocals, pos)
        perm = self.viper_ast.CurrentPerm(offer_pred, pos)
        expr = op(fresh_offered_get, old_offered_get, perm)
        trigger = self.viper_ast.Trigger([fresh_offered_get], pos)
        quant = self.viper_ast.Forall(qvars, [trigger], expr, pos)
        assume = self.viper_ast.Inhale(quant, pos)
        res.append(assume)

        # Assume the no_offers stayed the same for all others
        qvar_types = 1 * [helpers.struct_type(self.viper_ast)] + 1 * [self.viper_ast.Int]
        qvars = [self.viper_ast.LocalVarDecl(f'$arg{i}', t, pos) for i, t in enumerate(qvar_types)]
        qlocals = [var.localVar() for var in qvars]
        context_qvars = [qvar.local_var(ctx) for qvar in ctx.quantified_vars.values()]

        fresh_no_offers = helpers.no_offers(self.viper_ast, fresh_offered, *qlocals, pos)
        old_no_offers = helpers.no_offers(self.viper_ast, offered, *qlocals, pos)
        nodes_in_from_resource = self.viper_ast.to_list(from_resource)
        if any(qvar in nodes_in_from_resource for qvar in context_qvars):
            resource_eq = self.viper_ast.TrueLit()
        else:
            resource_eq = self.viper_ast.EqCmp(qlocals[0], from_resource, pos)
        nodes_in_from_owner = self.viper_ast.to_list(from_owner)
        if any(qvar in nodes_in_from_owner for qvar in context_qvars):
            address_eq = self.viper_ast.TrueLit()
        else:
            address_eq = self.viper_ast.EqCmp(qlocals[1], from_owner, pos)
        cond = self.viper_ast.Not(self.viper_ast.And(resource_eq, address_eq, pos), pos)
        expr = self.viper_ast.EqCmp(fresh_no_offers, old_no_offers, pos)
        expr = self.viper_ast.Implies(cond, expr, pos)
        trigger = self.viper_ast.Trigger([fresh_no_offers], pos)
        quant = self.viper_ast.Forall(qvars, [trigger], expr, pos)
        assume = self.viper_ast.Inhale(quant, pos)
        res.append(assume)

        # Set the new offered
        offered_assign = self.viper_ast.LocalVarAssign(offered, fresh_offered, pos)
        res.append(offered_assign)

        # Heap clean-up
        self._exhale_offers(res, ctx, pos)

    def _inhale_offers(self,
                       from_resource: Expr, to_resource: Expr,
                       from_val: Expr, to_val: Expr,
                       from_addr: Expr, to_addr: Expr,
                       amount: Expr,
                       res: List[Stmt], ctx: Context, pos=None):
        offer = helpers.offer_predicate(self.viper_ast, from_resource, to_resource, from_val,
                                        to_val, from_addr, to_addr, pos)
        perm = self.viper_ast.IntPermMul(amount, self.viper_ast.FullPerm(pos), pos)
        acc_offer = self.viper_ast.PredicateAccessPredicate(offer, perm, pos)
        trigger = self.viper_ast.Trigger([offer], pos)
        quant = self._quantifier(acc_offer, [trigger], ctx, pos)
        # TODO: rule
        res.append(self.viper_ast.Inhale(quant, pos))

    def _exhale_offers(self, res: List[Stmt], _: Context, pos=None):
        # We clean up the heap by exhaling all permissions to offer.
        #   exhale forall a, b, c, d: Int :: perm(offer(a, b, c, d)) > none ==>
        #   acc(offer(a, b, c, d), perm(offer(a, b, c, d)))
        # We use an implication with a '> none' because of a bug in Carbon (TODO: issue #171) where it isn't possible
        # to exhale no permissions under a quantifier.
        qvar_types = 2 * [helpers.struct_type(self.viper_ast)] + 4 * [self.viper_ast.Int]
        qvars = [self.viper_ast.LocalVarDecl(f'$arg{i}', t, pos) for i, t in enumerate(qvar_types)]
        qvars_locals = [var.localVar() for var in qvars]
        offer = helpers.offer_predicate(self.viper_ast, *qvars_locals, pos)
        perm = self.viper_ast.CurrentPerm(offer, pos)
        cond = self.viper_ast.GtCmp(perm, self.viper_ast.NoPerm(pos), pos)
        acc_offer = self.viper_ast.PredicateAccessPredicate(offer, perm, pos)
        trigger = self.viper_ast.Trigger([offer], pos)
        quant = self.viper_ast.Forall(qvars, [trigger], self.viper_ast.Implies(cond, acc_offer, pos), pos)
        # TODO: rule
        res.append(self.viper_ast.Exhale(quant, pos))

    def _if_non_zero_values(self, fun: Callable[[List[Stmt]], None], amounts: Union[List[Expr], Expr], res: List[Stmt],
                            ctx: Context, pos=None):
        then = []
        fun(then)
        zero = self.viper_ast.IntLit(0, pos)
        if isinstance(amounts, list):
            amount_checks = [self.viper_ast.NeCmp(amount, zero, pos) for amount in amounts]
            is_not_zero = reduce(self.viper_ast.And, amount_checks) if amount_checks else self.viper_ast.TrueLit()
        else:
            is_not_zero = self.viper_ast.NeCmp(amounts, zero, pos)
        if ctx.quantified_vars:
            quantified_vars = [q_var.var_decl(ctx) for q_var in ctx.quantified_vars.values()]
            is_not_zero = self.viper_ast.Forall(quantified_vars, [], is_not_zero)

        res.extend(helpers.flattened_conditional(self.viper_ast, is_not_zero, then, [], pos))

    def _check_trusted_if_non_zero_amount(self, node: ast.Node, address: Expr, by_address: Expr,
                                          amounts: Union[List[Expr], Expr], rule: rules.Rule, res: List[Stmt],
                                          ctx: Context, pos=None):
        """
        Only check trusted if all values are non-zero.
        """
        self._if_non_zero_values(lambda l: self._check_trusted(node, address, by_address, rule, l, ctx, pos),
                                 amounts, res, ctx, pos)

    def _check_trusted(self, node: ast.Node,
                       address: Expr, by_address: Expr,
                       rule: rules.Rule, res: List[Stmt], ctx: Context, pos=None):
        if ctx.inside_interface_call:
            return

        where = ctx.self_address or helpers.self_address(self.viper_ast, pos)

        trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx, pos)
        get_trusted = self.get_trusted(trusted, where, address, by_address, ctx, pos)
        eq = self.viper_ast.EqCmp(address, by_address, pos)
        cond = self.viper_ast.Or(eq, get_trusted, pos)
        if ctx.quantified_vars:
            trigger = self.viper_ast.Trigger([get_trusted], pos)
            cond = self._quantifier(cond, [trigger], ctx, pos)

        modelt = self.model_translator.save_variables(res, ctx, pos)
        combined_rule = rules.combine(rules.NOT_TRUSTED_FAIL, rule)
        apos = self.to_position(node, ctx, combined_rule, modelt=modelt)
        res.append(self.viper_ast.Assert(cond, apos))

    def _change_trusted(self,
                        address: Expr, by_address: Expr,
                        new_value: Expr,
                        res: List[Stmt], ctx: Context, pos=None):
        where = ctx.self_address or helpers.self_address(self.viper_ast, pos)

        trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx, pos)
        set_trusted = self.set_trusted(trusted, where, address, by_address, new_value, ctx, pos)
        trusted_assign = self.viper_ast.LocalVarAssign(trusted, set_trusted, pos)
        res.append(trusted_assign)

    def _foreach_change_trusted(self,
                                address: Expr, by_address: Expr,
                                new_value: Expr,
                                res: List[Stmt], ctx: Context, pos=None):
        where = ctx.self_address or helpers.self_address(self.viper_ast, pos)
        trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx, pos)

        self._inhale_trust(where, address, by_address, res, ctx, pos)

        trusted_type = self.type_translator.translate(helpers.trusted_type(), ctx)
        fresh_trusted_name = ctx.new_local_var_name(names.TRUSTED)
        fresh_trusted_decl = self.viper_ast.LocalVarDecl(fresh_trusted_name, trusted_type, pos)
        ctx.new_local_vars.append(fresh_trusted_decl)
        fresh_trusted = fresh_trusted_decl.localVar()

        # Assume the values of the new map
        qaddr = self.viper_ast.LocalVarDecl('$a', self.viper_ast.Int, pos)
        qaddr_var = qaddr.localVar()
        qby = self.viper_ast.LocalVarDecl('$b', self.viper_ast.Int, pos)
        qby_var = qby.localVar()
        qwhere = self.viper_ast.LocalVarDecl('$c', self.viper_ast.Int, pos)
        qwhere_var = qwhere.localVar()

        fresh_trusted_get = self.get_trusted(fresh_trusted, qwhere_var, qaddr_var, qby_var, ctx, pos)
        old_trusted_get = self.get_trusted(trusted, qwhere_var, qaddr_var, qby_var, ctx, pos)
        trust_pred = helpers.trust_predicate(self.viper_ast, qwhere_var, qaddr_var, qby_var, pos)
        perm = self.viper_ast.CurrentPerm(trust_pred, pos)
        gtz = self.viper_ast.PermGtCmp(perm, self.viper_ast.NoPerm(pos), pos)
        cond = self.viper_ast.CondExp(gtz, new_value, old_trusted_get, pos)
        eq = self.viper_ast.EqCmp(fresh_trusted_get, cond, pos)
        trigger = self.viper_ast.Trigger([fresh_trusted_get], pos)
        quant = self.viper_ast.Forall([qaddr, qby, qwhere], [trigger], eq, pos)
        assume = self.viper_ast.Inhale(quant, pos)
        res.append(assume)

        # Assume the trust_no_one stayed the same for all others
        qvar_types = [self.viper_ast.Int, self.viper_ast.Int]
        qvars = [self.viper_ast.LocalVarDecl(f'$arg{i}', t, pos) for i, t in enumerate(qvar_types)]
        qlocals = [var.localVar() for var in qvars]
        context_qvars = [qvar.local_var(ctx) for qvar in ctx.quantified_vars.values()]

        fresh_trust_no_one = helpers.trust_no_one(self.viper_ast, fresh_trusted, *qlocals, pos)
        old_trust_no_one = helpers.trust_no_one(self.viper_ast, trusted, *qlocals, pos)
        nodes_in_by_address = self.viper_ast.to_list(by_address)
        if any(qvar in nodes_in_by_address for qvar in context_qvars):
            by_address_eq = self.viper_ast.TrueLit()
        else:
            by_address_eq = self.viper_ast.EqCmp(qlocals[0], by_address, pos)
        nodes_in_where = self.viper_ast.to_list(where)
        if any(qvar in nodes_in_where for qvar in context_qvars):
            where_eq = self.viper_ast.TrueLit()
        else:
            where_eq = self.viper_ast.EqCmp(qlocals[1], where, pos)
        cond = self.viper_ast.Not(self.viper_ast.And(by_address_eq, where_eq, pos), pos)
        expr = self.viper_ast.EqCmp(fresh_trust_no_one, old_trust_no_one, pos)
        expr = self.viper_ast.Implies(cond, expr, pos)
        trigger = self.viper_ast.Trigger([fresh_trust_no_one], pos)
        quant = self.viper_ast.Forall(qvars, [trigger], expr, pos)
        assume = self.viper_ast.Inhale(quant, pos)
        res.append(assume)

        # Set the new trusted
        trusted_assign = self.viper_ast.LocalVarAssign(trusted, fresh_trusted, pos)
        res.append(trusted_assign)

        # Heap clean-up
        self._exhale_trust(res, ctx, pos)

    def _inhale_trust(self, where: Expr, address: Expr, by_address: Expr, res: List[Stmt], ctx: Context, pos=None):
        trust = helpers.trust_predicate(self.viper_ast, where, address, by_address, pos)
        perm = self.viper_ast.FullPerm(pos)
        acc_trust = self.viper_ast.PredicateAccessPredicate(trust, perm, pos)
        trigger = self.viper_ast.Trigger([trust], pos)
        quant = self._quantifier(acc_trust, [trigger], ctx, pos)
        # TODO: rule
        res.append(self.viper_ast.Inhale(quant, pos))

    def _performs_acc_predicate(self, function: str, args: List[Expr], ctx: Context, pos=None) -> Expr:
        pred = helpers.performs_predicate(self.viper_ast, function, args, pos)
        cond = self.viper_ast.PredicateAccessPredicate(pred, self.viper_ast.FullPerm(pos), pos)
        if ctx.quantified_vars:
            cond = self._quantifier(cond, [], ctx, pos)

        return cond

    def _exhale_performs_if_non_zero_amount(self, node: ast.Node, function: str, args: List[Expr],
                                            amounts: Union[List[Expr], Expr], rule: Rule, res: List[Stmt],
                                            ctx: Context, pos=None):
        self._if_non_zero_values(lambda l: self._exhale_performs(node, function, args, rule, l, ctx, pos),
                                 amounts, res, ctx, pos)

    def _exhale_performs(self, node: ast.Node, function: str, args: List[Expr], rule: Rule, res: List[Stmt],
                         ctx: Context, pos=None):
        if ctx.program.config.has_option(names.CONFIG_NO_PERFORMS):
            return
        if ctx.inside_interface_call:
            return

        pred_access_pred = self._performs_acc_predicate(function, args, ctx, pos)
        modelt = self.model_translator.save_variables(res, ctx, pos)
        combined_rule = rules.combine(rules.NO_PERFORMS_FAIL, rule)
        apos = self.to_position(node, ctx, combined_rule, modelt=modelt)

        res.append(self.viper_ast.Exhale(pred_access_pred, apos))

    def check_performs(self, node: ast.Node, function: str, args: List[Expr], amounts: Union[List[Expr], Expr],
                       rule: Rule, res: List[Stmt], ctx: Context, pos=None):
        self._exhale_performs_if_non_zero_amount(node, function, args, amounts, rule, res, ctx, pos)

    def allocate_derived(self, node: ast.Node,
                         resource: Expr, address: Expr, actor: Expr, amount: Expr,
                         res: List[Stmt], ctx: Context, pos=None):

        with ctx.self_address_scope(helpers.self_address(self.viper_ast)):
            self._check_trusted_if_non_zero_amount(node, actor, address, amount, rules.PAYABLE_FAIL, res, ctx, pos)
        self.allocate(resource, address, amount, res, ctx, pos)
        self.check_performs(node, names.RESOURCE_PAYABLE, [resource, address, amount], [amount],
                            rules.PAYABLE_FAIL, res, ctx, pos)

    def allocate(self,
                 resource: Expr, address: Expr, amount: Expr,
                 res: List[Stmt], ctx: Context, pos=None):
        """
        Adds `amount` allocation to the allocation map entry of `address`.
        """
        self._change_allocation(resource, address, amount, True, res, ctx, pos)

    def reallocate(self, node: ast.Node,
                   resource: Expr, frm: Expr, to: Expr, amount: Expr, actor: Expr,
                   res: List[Stmt], ctx: Context, pos=None):
        """
        Checks that `from` has sufficient allocation and then moves `amount` allocation from `frm` to `to`.
        """
        stmts = []
        self._exhale_performs_if_non_zero_amount(node, names.REALLOCATE, [resource, frm, to, amount], amount,
                                                 rules.REALLOCATE_FAIL, stmts, ctx, pos)

        self._check_trusted_if_non_zero_amount(node, actor, frm, amount, rules.REALLOCATE_FAIL, stmts, ctx, pos)
        self._check_allocation(node, resource, frm, amount, rules.REALLOCATE_FAIL_INSUFFICIENT_FUNDS, stmts, ctx, pos)
        self._change_allocation(resource, frm, amount, False, stmts, ctx, pos)
        self._change_allocation(resource, to, amount, True, stmts, ctx, pos)

        self.seqn_with_info(stmts, "Reallocate", res)

    def deallocate_wei(self, node: ast.Node,
                       address: Expr, amount: Expr,
                       res: List[Stmt], ctx: Context, pos=None):
        no_derived_wei = ctx.program.config.has_option(names.CONFIG_NO_DERIVED_WEI)

        if no_derived_wei:
            resource, underlying_resource = None, self.resource_translator.underlying_wei_resource(ctx)
        else:
            resource, underlying_resource = self.resource_translator.translate_with_underlying(None, res, ctx)
        self_address = ctx.self_address or helpers.self_address(self.viper_ast)

        self.interface_performed(node, names.REALLOCATE, [underlying_resource, self_address, address, amount],
                                 amount, res, ctx, pos)

        if no_derived_wei:
            return
        self.deallocate_derived(node, resource, underlying_resource, address, amount, res, ctx, pos)

    def deallocate_derived(self, node: ast.Node,
                           resource: Expr, underlying_resource: Expr, address: Expr, amount: Expr,
                           res: List[Stmt], ctx: Context, pos=None):
        """
        Checks that `address` has sufficient allocation and then removes `amount` allocation
        from the allocation map entry of `address`.
        """
        stmts = []
        const_one = self.viper_ast.IntLit(1, pos)

        self._exhale_performs_if_non_zero_amount(node, names.RESOURCE_PAYOUT, [resource, address, amount], amount,
                                                 rules.PAYOUT_FAIL, stmts, ctx, pos)

        offer_check_stmts = []

        def check_offer(then):
            self._check_from_agrees(node, resource, underlying_resource, const_one, const_one,
                                    address, address, amount, then, ctx, pos)
            self._change_offered(resource, underlying_resource, const_one, const_one,
                                 address, address, amount, False, then, ctx, pos)
        self._if_non_zero_values(check_offer, amount, offer_check_stmts, ctx, pos)

        # Only check that there was an offer, if someone else than a trusted address performs the deallocation
        msg_sender = helpers.msg_sender(self.viper_ast, ctx, pos)
        where = ctx.self_address or helpers.self_address(self.viper_ast, pos)
        trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx, pos)
        is_trusted_address = self.get_trusted(trusted, where, msg_sender, address, ctx, pos)
        is_itself = self.viper_ast.EqCmp(msg_sender, address, pos)
        is_trusted_address = self.viper_ast.Or(is_itself, is_trusted_address, pos)
        not_trusted_address = self.viper_ast.Not(is_trusted_address, pos)
        stmts.extend(helpers.flattened_conditional(self.viper_ast, not_trusted_address, offer_check_stmts, [], pos))

        self._check_allocation(node, resource, address, amount, rules.REALLOCATE_FAIL_INSUFFICIENT_FUNDS,
                               stmts, ctx, pos)
        self._change_allocation(resource, address, amount, False, stmts, ctx, pos)

        self.seqn_with_info(stmts, "Deallocate", res)

    def create(self, node: ast.Node,
               resource: Expr, frm: Expr, to: Expr, amount: Expr, actor: Expr,
               is_init: bool,
               res: List[Stmt], ctx: Context, pos=None):
        stmts = []

        self._exhale_performs_if_non_zero_amount(node, names.CREATE, [resource, frm, to, amount], amount,
                                                 rules.CREATE_FAIL, stmts, ctx, pos)

        # The initializer is allowed to create all resources unchecked.
        if not is_init:
            def check(then):
                self._check_trusted(node, actor, frm, rules.CREATE_FAIL, then, ctx, pos)
                creator_resource = self.resource_translator.creator_resource(resource, ctx, pos)
                self._check_creator(node, creator_resource, frm, amount, then, ctx, pos)
            self._if_non_zero_values(check, amount, res, ctx, pos)

        if ctx.quantified_vars:

            def op(fresh: Expr, old: Expr, perm: Expr) -> Expr:
                write = self.viper_ast.FullPerm(pos)
                fresh_mul = self.viper_ast.IntPermMul(fresh, write, pos)
                old_mul = self.viper_ast.IntPermMul(old, write, pos)
                perm_add = self.viper_ast.PermAdd(old_mul, perm, pos)
                return self.viper_ast.EqCmp(fresh_mul, perm_add, pos)

            self._foreach_change_allocation(resource, to, amount, op, stmts, ctx, pos)
        else:
            self.allocate(resource, to, amount, stmts, ctx, pos)

        self.seqn_with_info(stmts, "Create", res)

    def destroy(self, node: ast.Node,
                resource: Expr, address: Expr, amount: Expr, actor: Expr,
                res: List[Stmt], ctx: Context, pos=None):
        """
        Checks that `address` has sufficient allocation and then removes `amount` allocation
        from the allocation map entry of `address`.
        """
        stmts = []
        self._exhale_performs_if_non_zero_amount(node, names.DESTROY, [resource, address, amount], amount,
                                                 rules.DESTROY_FAIL, stmts, ctx, pos)

        self._check_trusted_if_non_zero_amount(node, actor, address, amount, rules.DESTROY_FAIL, stmts, ctx, pos)
        self._check_allocation(node, resource, address, amount, rules.DESTROY_FAIL_INSUFFICIENT_FUNDS, stmts, ctx, pos)

        if ctx.quantified_vars:

            def op(fresh: Expr, old: Expr, perm: Expr) -> Expr:
                write = self.viper_ast.FullPerm(pos)
                fresh_mul = self.viper_ast.IntPermMul(fresh, write, pos)
                old_mul = self.viper_ast.IntPermMul(old, write, pos)
                perm_sub = self.viper_ast.PermSub(old_mul, perm, pos)
                return self.viper_ast.EqCmp(fresh_mul, perm_sub, pos)

            self._foreach_change_allocation(resource, address, amount, op, stmts, ctx, pos)
        else:
            self._change_allocation(resource, address, amount, False, stmts, ctx, pos)

        return self.seqn_with_info(stmts, "Destroy", res)

    def _allocation_leak_check(self, node: ast.Node, rule: Rule, res: List[Stmt], ctx: Context, pos=None):
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

        # Assume type assumptions for fresh_allocated
        allocated_ass = self.type_translator.type_assumptions(fresh_allocated_var, fresh_allocated.type, ctx)
        allocated_assumptions = [self.viper_ast.Inhale(c) for c in allocated_ass]
        allocated_info_msg = "Assume type assumptions for fresh allocated"
        self.seqn_with_info(allocated_assumptions, allocated_info_msg, res)

        with ctx.allocated_scope(fresh_allocated):
            # We assume the invariant with the current state as the old state because the current allocation
            # should be known from the current state, not the old state. For example, the invariant
            #   allocated() == old(allocated())
            # should be illegal.
            with ctx.state_scope(ctx.current_state, ctx.current_state):
                for inv in ctx.unchecked_invariants():
                    res.append(self.viper_ast.Inhale(inv))

                # As an optimization we only assume invariants that mention allocated(), all other invariants
                # are already known since we only changed the allocation map to a fresh one
                contracts: List[VyperProgram] = [ctx.program.interfaces[i.name] for i in ctx.program.implements]
                contracts.append(ctx.program)
                for contract in contracts:
                    with ctx.program_scope(contract):
                        for inv in ctx.current_program.analysis.allocated_invariants:
                            ppos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                            expr = spec_translator.translate_invariant(inv, res, ctx, True)
                            res.append(self.viper_ast.Inhale(expr, ppos))

        modelt = self.model_translator.save_variables(res, ctx, pos)

        # We create the following check for each resource r:
        #   forall a: address, arg0, arg1, ... :: <type_assumptions> ==>
        #      allocated[r(arg0, arg1, ...)](a) == fresh_allocated[r(arg0, arg1, ...)](a)
        address = self.viper_ast.LocalVarDecl('$a', self.viper_ast.Int, pos)
        address_var = address.localVar()
        address_assumptions = self.type_translator.type_assumptions(address_var, types.VYPER_ADDRESS, ctx)

        interface_names = [t.name for t in ctx.program.implements]
        interfaces = [ctx.program.interfaces[name] for name in interface_names]
        own_resources = [(name, resource) for name, resource in ctx.program.own_resources.items()
                         # Do not make a leak check for the underlying wei resource
                         if name != names.UNDERLYING_WEI]
        for i in interfaces:
            interface_resources = [(name, resource) for name, resource in i.own_resources.items()
                                   # Do not make a leak check for the underlying wei resource
                                   if name != names.UNDERLYING_WEI]
            own_resources.extend(interface_resources)

        for name, resource in own_resources:
            type_assumptions = address_assumptions.copy()
            args = []
            for idx, arg_type in enumerate(resource.type.member_types.values()):
                viper_type = self.type_translator.translate(arg_type, ctx)
                arg = self.viper_ast.LocalVarDecl(f'$arg{idx}', viper_type, pos)
                args.append(arg)
                arg_var = arg.localVar()
                type_assumptions.extend(self.type_translator.type_assumptions(arg_var, arg_type, ctx))

            cond = reduce(lambda l, r: self.viper_ast.And(l, r, pos), type_assumptions)

            t_resource = self.resource_translator.resource(name, [arg.localVar() for arg in args], ctx)
            allocated_get = self.get_allocated(allocated.local_var(ctx, pos), t_resource, address_var, ctx, pos)
            fresh_allocated_get = self.get_allocated(fresh_allocated_var, t_resource, address_var, ctx, pos)
            allocated_eq = self.viper_ast.EqCmp(allocated_get, fresh_allocated_get, pos)
            trigger = self.viper_ast.Trigger([allocated_get, fresh_allocated_get], pos)
            assertion = self.viper_ast.Forall([address, *args], [trigger],
                                              self.viper_ast.Implies(cond, allocated_eq, pos), pos)
            if ctx.function.name == names.INIT:
                # Leak check only has to hold if __init__ succeeds
                succ = ctx.success_var.local_var(ctx, pos)
                assertion = self.viper_ast.Implies(succ, assertion, pos)

            apos = self.to_position(node, ctx, rule, modelt=modelt, values={'resource': resource})
            res.append(self.viper_ast.Assert(assertion, apos))

    def _performs_leak_check(self, node: ast.Node, res: List[Stmt], ctx: Context, pos=None):
        if not ctx.program.config.has_option(names.CONFIG_NO_PERFORMS):
            struct_t = helpers.struct_type(self.viper_ast)
            int_t = self.viper_ast.Int
            bool_t = self.viper_ast.Bool

            predicate_types = {
                names.CREATE: [struct_t, int_t, int_t, int_t],
                names.DESTROY: [struct_t, int_t, int_t],
                names.REALLOCATE: [struct_t, int_t, int_t, int_t],
                # ALLOW_TO_DECOMPOSE is modelled as an offer and therefore needs no leak check
                names.OFFER: [struct_t, struct_t, int_t, int_t, int_t, int_t, int_t],
                names.REVOKE: [struct_t, struct_t, int_t, int_t, int_t, int_t],
                names.EXCHANGE: [struct_t, struct_t, int_t, int_t, int_t, int_t, int_t],
                names.TRUST: [int_t, int_t, bool_t],
                names.ALLOCATE_UNTRACKED: [struct_t, int_t],
                names.RESOURCE_PAYABLE: [struct_t, int_t, int_t],
                names.RESOURCE_PAYOUT: [struct_t, int_t, int_t],
            }

            modelt = self.model_translator.save_variables(res, ctx, pos)

            for function, arg_types in predicate_types.items():
                # We could use forperm instead, but Carbon doesn't support multiple variables
                # in forperm (TODO: issue #243)
                quant_decls = [self.viper_ast.LocalVarDecl(f'$a{idx}', t, pos) for idx, t in enumerate(arg_types)]
                quant_vars = [decl.localVar() for decl in quant_decls]
                pred = helpers.performs_predicate(self.viper_ast, function, quant_vars, pos)
                succ = ctx.success_var.local_var(ctx, pos)
                perm = self.viper_ast.CurrentPerm(pred, pos)
                cond = self.viper_ast.Implies(succ, self.viper_ast.EqCmp(perm, self.viper_ast.NoPerm(pos), pos), pos)
                trigger = self.viper_ast.Trigger([pred], pos)
                quant = self.viper_ast.Forall(quant_decls, [trigger], cond, pos)
                apos = self.to_position(node, ctx, rules.PERFORMS_LEAK_CHECK_FAIL, modelt=modelt)
                res.append(self.viper_ast.Assert(quant, apos))

    def function_leak_check(self, res: List[Stmt], ctx: Context, pos=None):
        self._allocation_leak_check(ctx.function.node or ctx.program.node, rules.ALLOCATION_LEAK_CHECK_FAIL,
                                    res, ctx, pos)
        self._performs_leak_check(ctx.function.node or ctx.program.node, res, ctx, pos)

    def send_leak_check(self, node: ast.Node, res: List[Stmt], ctx: Context, pos=None):
        self._allocation_leak_check(node, rules.CALL_LEAK_CHECK_FAIL, res, ctx, pos)

    def offer(self, node: ast.Node,
              from_resource: Expr, to_resource: Expr,
              from_value: Expr, to_value: Expr,
              from_owner: Expr, to_owner: Expr,
              times: Expr, actor: Expr,
              res: List[Stmt], ctx: Context, pos=None):
        stmts = []

        self._exhale_performs_if_non_zero_amount(node, names.OFFER, [from_resource, to_resource, from_value,
                                                                     to_value, from_owner, to_owner, times],
                                                 [from_value, times], rules.OFFER_FAIL, stmts, ctx, pos)

        self._check_trusted_if_non_zero_amount(node, actor, from_owner, [from_value, times],
                                               rules.OFFER_FAIL, stmts, ctx, pos)

        if ctx.quantified_vars:
            # We are translating a
            #   foreach({x1: t1, x2: t2, ...}, offer(e1(x1, x2, ...), e2(x1, x2, ...), to=e3(x1, x2, ...), times=t))
            # To do that, we first inhale the offer predicate
            #   inhale forall x1: t1, x2: t2, ... :: acc(offer(e1(...), e2(...), ..., e3(...)), t * write)
            # For all offers we inhaled some permission to we then set the 'times'  entries in a new map to the
            # sum of the old map entries and the current permissions to the respective offer.
            # assume forall $i, $j, $a, $b: Int ::
            #    fresh_offered[{$i, $j, $a, $b}] * write == old_offered[...] * write + perm(offer($i, $j, $a, $b))

            def op(fresh: Expr, old: Expr, perm: Expr) -> Expr:
                write = self.viper_ast.FullPerm(pos)
                fresh_mul = self.viper_ast.IntPermMul(fresh, write, pos)
                old_mul = self.viper_ast.IntPermMul(old, write, pos)
                perm_add = self.viper_ast.PermAdd(old_mul, perm, pos)
                return self.viper_ast.EqCmp(fresh_mul, perm_add, pos)

            self._foreach_change_offered(from_resource, to_resource, from_value, to_value, from_owner, to_owner, times,
                                         op, stmts, ctx, pos)
        else:
            self._change_offered(from_resource, to_resource, from_value, to_value, from_owner, to_owner, times, True,
                                 stmts, ctx, pos)

        self.seqn_with_info(stmts, "Offer", res)

    def allow_to_decompose(self, node: ast.Node,
                           resource: Expr, underlying_resource: Expr,
                           owner: Expr, amount: Expr, actor: Expr,
                           res: List[Stmt], ctx: Context, pos=None):
        stmts = []
        const_one = self.viper_ast.IntLit(1, pos)

        self._exhale_performs_if_non_zero_amount(node, names.OFFER, [resource, underlying_resource, const_one,
                                                                     const_one, owner, owner, amount],
                                                 amount, rules.OFFER_FAIL, stmts, ctx, pos)

        self._check_trusted_if_non_zero_amount(node, actor, owner, amount,
                                               rules.OFFER_FAIL, stmts, ctx, pos)

        self._set_offered(resource, underlying_resource, const_one, const_one, owner, owner, amount, stmts, ctx, pos)

        self.seqn_with_info(stmts, "Allow to decompose", res)

    def revoke(self, node: ast.Node,
               from_resource: Expr, to_resource: Expr,
               from_value: Expr, to_value: Expr,
               from_owner: Expr, to_owner: Expr,
               actor: Expr,
               res: List[Stmt], ctx: Context, pos=None):
        stmts = []
        self._exhale_performs_if_non_zero_amount(node, names.REVOKE, [from_resource, to_resource, from_value,
                                                                      to_value, from_owner, to_owner],
                                                 from_value, rules.REVOKE_FAIL, stmts, ctx, pos)

        self._check_trusted_if_non_zero_amount(node, actor, from_owner, from_value, rules.REVOKE_FAIL, stmts, ctx, pos)
        if ctx.quantified_vars:
            # We are translating a
            #   foreach({x1: t1, x2: t2, ...}, revoke(e1(x1, x2, ...), e2(x1, x2, ...), to=e3(x1, x2, ...)))
            # To do that, we first inhale the offer predicate
            #   inhale forall x1: t1, x2: t2, ... :: offer(e1(...), e2(...), ..., e3(...))
            # For all offers we inhaled some permission to we then set the 'times' entries to zero in a
            # new map, all others stay the same. assume forall $i, $j, $a, $b: Int ::
            #    fresh_offered[{$i, $j, $a, $b}] == perm(offer($i, $j, $a, $b)) > none ? 0 : old_offered[...]
            one = self.viper_ast.IntLit(1, pos)

            def op(fresh: Expr, old: Expr, perm: Expr) -> Expr:
                gez = self.viper_ast.GtCmp(perm, self.viper_ast.NoPerm(pos), pos)
                cond_expr = self.viper_ast.CondExp(gez, self.viper_ast.IntLit(0, pos), old, pos)
                return self.viper_ast.EqCmp(fresh, cond_expr, pos)

            self._foreach_change_offered(from_resource, to_resource, from_value, to_value, from_owner, to_owner, one,
                                         op, stmts, ctx, pos)
        else:
            zero = self.viper_ast.IntLit(0, pos)
            self._set_offered(from_resource, to_resource, from_value, to_value, from_owner, to_owner, zero,
                              stmts, ctx, pos)

        self.seqn_with_info(stmts, "Revoke", res)

    def exchange(self,
                 node: ast.Node,
                 resource1: Expr, resource2: Expr,
                 value1: Expr, value2: Expr,
                 owner1: Expr, owner2: Expr,
                 times: Expr,
                 res: List[Stmt], ctx: Context, pos=None):
        stmts = []
        self._exhale_performs_if_non_zero_amount(node, names.EXCHANGE, [resource1, resource2, value1, value2,
                                                                        owner1, owner2, times],
                                                 [self.viper_ast.Add(value1, value2), times], rules.EXCHANGE_FAIL,
                                                 stmts, ctx, pos)

        def check_owner_1(then):
            # If value1 == 0, owner1 will definitely agree, else we check that they offered the exchange, and
            # decreases the offer map by the amount of exchanges we do
            self._check_from_agrees(node, resource1, resource2, value1, value2, owner1, owner2, times, then, ctx, pos)
            self._change_offered(resource1, resource2, value1, value2, owner1, owner2, times, False, then, ctx, pos)
        self._if_non_zero_values(check_owner_1, [value1, times], stmts, ctx, pos)

        def check_owner_2(then):
            # We do the same for owner2
            self._check_from_agrees(node, resource2, resource1, value2, value1, owner2, owner1, times, then, ctx, pos)
            self._change_offered(resource2, resource1, value2, value1, owner2, owner1, times, False, then, ctx, pos)
        self._if_non_zero_values(check_owner_2, [value2, times], stmts, ctx, pos)

        amount1 = self.viper_ast.Mul(times, value1)
        self._check_allocation(node, resource1, owner1, amount1, rules.EXCHANGE_FAIL_INSUFFICIENT_FUNDS,
                               stmts, ctx, pos)

        amount2 = self.viper_ast.Mul(times, value2)
        self._check_allocation(node, resource2, owner2, amount2, rules.EXCHANGE_FAIL_INSUFFICIENT_FUNDS,
                               stmts, ctx, pos)

        # owner1 gives up amount1 of resource1
        self._change_allocation(resource1, owner1, amount1, False, stmts, ctx, pos)
        # owner1 gets amount2 of resource2
        self._change_allocation(resource2, owner1, amount2, True, stmts, ctx, pos)

        # owner2 gives up amount2 of resource2
        self._change_allocation(resource2, owner2, amount2, False, stmts, ctx, pos)
        # owner2 gets amount1 of resource1
        self._change_allocation(resource1, owner2, amount1, True, stmts, ctx, pos)

        self.seqn_with_info(stmts, "Exchange", res)

    def trust(self, node: ast.Node,
              address: Expr, from_address: Expr,
              new_value: Expr, res: List[Stmt],
              ctx: Context, pos=None):
        stmts = []

        self._exhale_performs(node, names.TRUST, [address, from_address, new_value],
                              rules.TRUST_FAIL, stmts, ctx, pos)

        if ctx.quantified_vars:
            self._foreach_change_trusted(address, from_address, new_value, stmts, ctx, pos)
        else:
            self._change_trusted(address, from_address, new_value, stmts, ctx, pos)

        self.seqn_with_info(stmts, "Trust", res)

    def allocate_untracked(self, node: ast.Node, resource: Expr, address: Expr, balance: Expr,
                           res: List[Stmt], ctx: Context, pos=None):
        stmts = []
        self._exhale_performs(node, names.ALLOCATE_UNTRACKED, [resource, address],
                              rules.ALLOCATE_UNTRACKED_FAIL, stmts, ctx, pos)

        difference = self.allocation_difference_to_balance(balance, resource, ctx, pos)
        self.allocate(resource, address, difference, stmts, ctx, pos)

        self.seqn_with_info(stmts, "Allocate untracked wei", res)

    def allocation_difference_to_balance(self, balance: Expr, resource: Expr, ctx: Context, pos=None):
        allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx)
        allocated_map = self.get_allocated_map(allocated, resource, ctx, pos)
        key_type = self.type_translator.translate(helpers.allocated_type().value_type.key_type, ctx)
        allocated_sum = helpers.map_sum(self.viper_ast, allocated_map, key_type, pos)
        difference = self.viper_ast.Sub(balance, allocated_sum, pos)
        return difference

    def performs(self, _: ast.Node, resource_function_name: str, args: List[Expr],
                 amount_args: Union[List[Expr], Expr], res: List[Stmt], ctx: Context, pos=None):
        pred = self._performs_acc_predicate(resource_function_name, args, ctx, pos)
        # TODO: rule
        self._if_non_zero_values(lambda l: l.append(self.viper_ast.Inhale(pred, pos)), amount_args, res, ctx, pos)

    def interface_performed(self, node: ast.Node, resource_function_name: str, args: List[Expr],
                            amount_args: Union[List[Expr], Expr], res: List[Stmt], ctx: Context, pos=None):
        pred_access_pred = self._performs_acc_predicate(resource_function_name, args, ctx, pos)

        # Only exhale if we have enough "perm" (Redeclaration of performs is optional)
        pred = helpers.performs_predicate(self.viper_ast, resource_function_name, args, pos)
        perm = self.viper_ast.CurrentPerm(pred, pos)
        write = self.viper_ast.FullPerm(pos)
        enough_perm = self.viper_ast.GeCmp(perm, write, pos)

        # Only exhale if the address is not self and the resource is potentially an "own resource"
        address = None
        if isinstance(node, ast.FunctionCall) and node.name in names.GHOST_STATEMENTS:
            interface_files = [ctx.program.interfaces[impl.name].file for impl in ctx.program.implements]
            address, resource = self.location_address_of_performs(node, res, ctx, pos, return_resource=True)
            if resource is not None and (resource.file is None  # It is okay to declare performs for wei
                                         # It is okay to declare performs for own private resources
                                         or resource.file == ctx.program.file
                                         # It is okay to redeclare performs with resources not in interfaces
                                         # this contract implements
                                         or resource.file not in interface_files):
                address = None
        if address is not None:
            self_address = helpers.self_address(self.viper_ast)
            address_cond = self.viper_ast.NeCmp(address, self_address, pos)
        else:
            address_cond = self.viper_ast.TrueLit(pos)

        cond = self.viper_ast.And(enough_perm, address_cond)
        cond_pred = self.viper_ast.CondExp(cond, pred_access_pred, self.viper_ast.TrueLit(), pos)

        # TODO: rule
        self._if_non_zero_values(lambda l: l.append(self.viper_ast.Exhale(cond_pred, pos)), amount_args, res, ctx, pos)

    def location_address_of_performs(self, node: ast.FunctionCall, res: List[Stmt], ctx: Context,
                                     pos=None, return_resource=False):
        if node.name == names.TRUST:
            res = ctx.self_address or helpers.self_address(self.viper_ast, pos), None
        elif node.name == names.FOREACH:
            body = node.args[-1]
            assert isinstance(body, ast.FunctionCall)
            res = self.location_address_of_performs(body, res, ctx, pos, True)
        else:
            # All other allocation functions have a resource with the location
            if isinstance(node.resource, ast.Exchange):
                (resource, t_resource), _ = self.resource_translator.translate_exchange(
                    node.resource, res, ctx, True)
            elif node.resource is not None:
                resource, t_resource = self.resource_translator.translate(node.resource, res, ctx, True)
            elif ctx.program.config.has_option(names.CONFIG_NO_DERIVED_WEI):
                resource, t_resource = None, self.resource_translator.underlying_wei_resource(ctx)
            else:
                resource, t_resource = self.resource_translator.translate(None, res, ctx, True)

            resource_args = self.viper_ast.to_list(t_resource.getArgs())
            if resource_args:
                res = resource_args.pop(), resource
            else:
                res = None, resource

        if return_resource:
            return res
        return res[0]
