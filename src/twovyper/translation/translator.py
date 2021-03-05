"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from functools import reduce
from itertools import chain
from typing import List, Optional

from twovyper import resources
from twovyper.translation.lemma import LemmaTranslator

from twovyper.utils import flatten, seq_to_list

from twovyper.ast import names, types, ast_nodes as ast
from twovyper.ast.nodes import VyperProgram, VyperEvent, VyperStruct, VyperFunction, GhostFunction, Resource
from twovyper.ast.types import AnyStructType

from twovyper.exceptions import ConsistencyException

from twovyper.translation import helpers, mangled, State
from twovyper.translation.context import Context
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.allocation import AllocationTranslator
from twovyper.translation.balance import BalanceTranslator
from twovyper.translation.function import FunctionTranslator
from twovyper.translation.pure_function import PureFunctionTranslator
from twovyper.translation.resource import ResourceTranslator
from twovyper.translation.specification import SpecificationTranslator
from twovyper.translation.state import StateTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar
from twovyper.translation.wrapped_viper_ast import WrappedViperAST

from twovyper.verification import rules

from twovyper.viper import sif
from twovyper.viper.ast import ViperAST
from twovyper.viper.jvmaccess import JVM
from twovyper.viper.parser import ViperParser
from twovyper.viper.typedefs import Program, Stmt


class TranslationOptions:

    def __init__(self, create_model: bool, check_ast_inconsistencies: bool):
        self.create_model = create_model
        self.check_ast_inconsistencies = check_ast_inconsistencies


builtins: Optional[Program] = None


def translate(vyper_program: VyperProgram, options: TranslationOptions, jvm: JVM) -> Program:
    viper_ast = ViperAST(jvm)
    if not viper_ast.is_available():
        raise Exception('Viper not found on classpath.')
    if not viper_ast.is_extension_available():
        raise Exception('Viper AST SIF extension not found on classpath.')

    if vyper_program.is_interface():
        return viper_ast.Program([], [], [], [], [])

    global builtins
    if builtins is None:
        viper_parser = ViperParser(jvm)
        builtins = viper_parser.parse(*resources.viper_all())
    translator = ProgramTranslator(viper_ast, builtins)

    viper_program = translator.translate(vyper_program, options)
    if options.check_ast_inconsistencies:
        consistency_errors = seq_to_list(viper_program.checkTransitively())
        if consistency_errors:
            raise ConsistencyException(viper_program, "The AST contains inconsistencies.", consistency_errors)

    sif.configure_mpp_transformation(jvm)
    viper_program = sif.transform(jvm, viper_program)
    return viper_program


class ProgramTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST, twovyper_builtins: Program):
        viper_ast = WrappedViperAST(viper_ast)
        super().__init__(viper_ast)
        self.builtins = twovyper_builtins
        self.allocation_translator = AllocationTranslator(viper_ast)
        self.function_translator = FunctionTranslator(viper_ast)
        self.pure_function_translator = PureFunctionTranslator(viper_ast)
        self.lemma_translator = LemmaTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)
        self.resource_translator = ResourceTranslator(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)
        self.state_translator = StateTranslator(viper_ast)
        self.balance_translator = BalanceTranslator(viper_ast)

    def translate(self, vyper_program: VyperProgram, options: TranslationOptions) -> Program:
        if names.INIT not in vyper_program.functions:
            vyper_program.functions[mangled.INIT] = helpers.init_function()

        # Add built-in methods
        methods = seq_to_list(self.builtins.methods())
        # Add built-in domains
        domains = seq_to_list(self.builtins.domains())
        # Add built-in functions
        functions = seq_to_list(self.builtins.functions())
        # Add built-in predicates
        predicates = seq_to_list(self.builtins.predicates())

        # Add self.$sent field
        sent_type = types.MapType(types.VYPER_ADDRESS, types.NON_NEGATIVE_INT)
        vyper_program.fields.type.add_member(mangled.SENT_FIELD, sent_type)
        # Add self.$received field
        received_type = types.MapType(types.VYPER_ADDRESS, types.NON_NEGATIVE_INT)
        vyper_program.fields.type.add_member(mangled.RECEIVED_FIELD, received_type)
        # Add self.$selfdestruct field
        selfdestruct_type = types.VYPER_BOOL
        vyper_program.fields.type.add_member(mangled.SELFDESTRUCT_FIELD, selfdestruct_type)
        # For each nonreentrant key add a boolean flag whether it is set
        for key in vyper_program.nonreentrant_keys():
            vyper_program.fields.type.add_member(mangled.lock_name(key), types.VYPER_BOOL)

        ctx = Context()
        ctx.program = vyper_program
        ctx.current_program = vyper_program
        ctx.options = options

        # Translate self
        domains.append(self._translate_struct(vyper_program.fields, ctx))

        for field, field_type in vyper_program.fields.type.member_types.items():
            ctx.field_types[field] = self.type_translator.translate(field_type, ctx)

        # Add the offer struct which we use as the key type of the offered map
        if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
            offer_struct = VyperStruct(mangled.OFFER, helpers.offer_type(), None)
            domains.append(self._translate_struct(offer_struct, ctx))

        def derived_resources_invariants(node: Optional[ast.Node] = None):
            if not ctx.program.config.has_option(names.CONFIG_ALLOCATION):
                return []

            derived_resources_invs = []
            trusted = ctx.current_state[mangled.TRUSTED].local_var(ctx)
            offered = ctx.current_state[mangled.OFFERED].local_var(ctx)

            self_address = ctx.self_address or helpers.self_address(self.viper_ast)

            own_derived_resources = [(name, resource) for name, resource in ctx.program.own_resources.items()
                                     if isinstance(resource.type, types.DerivedResourceType)]
            translated_own_derived_resources = self.resource_translator\
                .translate_resources_for_quantified_expr(own_derived_resources, ctx)
            translated_own_underlying_resources = self.resource_translator\
                .translate_resources_for_quantified_expr(own_derived_resources, ctx,
                                                         translate_underlying=True,
                                                         args_idx_start=len(translated_own_derived_resources))

            for index, (name, resource) in enumerate(own_derived_resources):
                if name == names.WEI:
                    continue

                pos_node = node or resource.node

                invariants = []
                assert resource.underlying_address is not None
                assert resource.underlying_resource is not None

                stmts = []
                t_underlying_address = self.specification_translator.translate(resource.underlying_address, stmts, ctx)
                with ctx.state_scope(ctx.current_old_state, ctx.current_old_state):
                    t_old_underlying_address = self.specification_translator.translate(resource.underlying_address,
                                                                                       stmts, ctx)
                assert not stmts
                # resource.underlying_address is not self
                pos = self.to_position(resource.node, ctx, rules.UNDERLYING_ADDRESS_SELF_FAIL,
                                       values={'resource': resource})
                underlying_address_not_self = self.viper_ast.NeCmp(t_underlying_address, self_address, pos)
                invariants.append(underlying_address_not_self)
                # resource.underlying_address is constant once set
                pos = self.to_position(pos_node, ctx, rules.UNDERLYING_ADDRESS_CONSTANT_FAIL,
                                       values={'resource': resource})
                old_underlying_address_neq_zero = self.viper_ast.NeCmp(t_old_underlying_address,
                                                                       self.viper_ast.IntLit(0), pos)
                underlying_address_eq = self.viper_ast.EqCmp(t_underlying_address, t_old_underlying_address, pos)
                underlying_address_const = self.viper_ast.Implies(old_underlying_address_neq_zero,
                                                                  underlying_address_eq, pos)
                invariants.append(underlying_address_const)
                # trust_no_one in resource.underlying_address
                pos = self.to_position(pos_node, ctx, rules.UNDERLYING_ADDRESS_TRUST_NO_ONE_FAIL,
                                       values={'resource': resource})
                trust_no_one = helpers.trust_no_one(self.viper_ast, trusted, self_address, t_underlying_address, pos)
                invariants.append(trust_no_one)
                # no_offers for resource.underlying_resource
                pos = self.to_position(pos_node, ctx, rules.UNDERLYING_RESOURCE_NO_OFFERS_FAIL,
                                       values={'resource': resource})
                t_resource, args, type_cond = translated_own_underlying_resources[index]
                no_offers = helpers.no_offers(self.viper_ast, offered, t_resource, self_address, pos)
                forall_no_offers = self.viper_ast.Forall([*args], [self.viper_ast.Trigger([no_offers], pos)],
                                                         self.viper_ast.Implies(type_cond, no_offers, pos), pos)
                invariants.append(forall_no_offers)
                # forall derived resource the underlying resource is different
                for i in range(index):
                    pos = self.to_position(pos_node, ctx, rules.UNDERLYING_RESOURCE_NEQ_FAIL,
                                           values={'resource': resource, 'other_resource': own_derived_resources[i][1]})
                    t_other_resource, other_args, other_type_cond = translated_own_underlying_resources[i]
                    neq_other_resource = self.viper_ast.NeCmp(t_resource, t_other_resource, pos)
                    and_type_cond = self.viper_ast.And(type_cond, other_type_cond, pos)
                    forall_neq_other_resource = self.viper_ast.Forall(
                        [*args, *other_args], [self.viper_ast.Trigger([t_resource, t_other_resource], pos)],
                        self.viper_ast.Implies(and_type_cond, neq_other_resource, pos), pos)
                    invariants.append(forall_neq_other_resource)
                derived_resources_invs.extend(invariants)
            return derived_resources_invs

        ctx.derived_resources_invariants = derived_resources_invariants

        def unchecked_invariants():
            res = []
            self_var = ctx.self_var.local_var(ctx)
            address_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)

            # forall({a: address}, {sent(a)}, sent(a) >= old(sent(a)))
            old_self_var = ctx.old_self_var.local_var(ctx)
            q_var = self.viper_ast.LocalVarDecl('$a', address_type)
            q_local = q_var.localVar()
            sent = self.balance_translator.get_sent(self_var, q_local, ctx)
            old_sent = self.balance_translator.get_sent(old_self_var, q_local, ctx)
            expr = self.viper_ast.GeCmp(sent, old_sent)
            trigger = self.viper_ast.Trigger([sent])
            sent_inc = self.viper_ast.Forall([q_var], [trigger], expr)
            res.append(sent_inc)

            if (ctx.program.config.has_option(names.CONFIG_ALLOCATION)
                    and not ctx.program.config.has_option(names.CONFIG_NO_DERIVED_WEI)):
                # self.balance >= sum(allocated())
                balance = self.balance_translator.get_balance(self_var, ctx)
                allocated = ctx.current_state[mangled.ALLOCATED].local_var(ctx)
                stmts = []
                wei_resource = self.resource_translator.translate(None, stmts, ctx)
                assert len(stmts) == 0
                allocated_map = self.allocation_translator.get_allocated_map(allocated, wei_resource, ctx)
                allocated_sum = helpers.map_sum(self.viper_ast, allocated_map, address_type)
                balance_geq_sum = self.viper_ast.GeCmp(balance, allocated_sum)
                res.append(balance_geq_sum)

            res.extend(derived_resources_invariants())
            return res

        def unchecked_transitive_postconditions():
            assume_locked = []
            for lock in ctx.program.nonreentrant_keys():
                with ctx.state_scope(ctx.current_old_state, ctx.current_old_state):
                    old_lock_val = helpers.get_lock(self.viper_ast, lock, ctx)
                with ctx.state_scope(ctx.current_state, ctx.current_state):
                    new_lock_val = helpers.get_lock(self.viper_ast, lock, ctx)
                assume_locked.append(self.viper_ast.EqCmp(old_lock_val, new_lock_val))
            return assume_locked

        ctx.unchecked_invariants = unchecked_invariants
        ctx.unchecked_transitive_postconditions = unchecked_transitive_postconditions

        # Structs
        structs = vyper_program.structs.values()
        domains.extend(self._translate_struct(struct, ctx) for struct in structs)

        # Resources
        all_resources = flatten(vyper_program.resources.values())
        domains.extend(self._translate_struct(resource, ctx) for resource in all_resources)
        domains.append(self._translate_struct(helpers.creator_resource(), ctx))

        # Ghost functions
        functions.extend(self._translate_ghost_function(func, ctx)
                         for func_list in vyper_program.ghost_functions.values() for func in func_list)
        domains.append(self._translate_implements(vyper_program, ctx))

        # Pure functions
        pure_vyper_functions = filter(VyperFunction.is_pure,  vyper_program.functions.values())
        functions += [self.pure_function_translator.translate(function, ctx) for function in pure_vyper_functions]

        # Lemmas
        functions += [function for lemma in vyper_program.lemmas.values()
                      for function in self.lemma_translator.translate(lemma, ctx)]

        # Events
        events = [self._translate_event(event, ctx) for event in vyper_program.events.values()]
        accs = [self._translate_accessible(acc, ctx) for acc in vyper_program.functions.values()]
        predicates.extend([*events, *accs])

        # Viper methods
        def translate_condition_for_vyper_function(func: VyperFunction) -> bool:
            has_general_postcondition = (len(vyper_program.general_postconditions) > 0
                                         or len(vyper_program.transitive_postconditions) > 0)
            if not has_general_postcondition and func.is_pure():
                has_loop_invariants = len(func.loop_invariants) > 0
                has_unreachable_assertions = func.analysis.uses_unreachable
                return has_loop_invariants or has_unreachable_assertions
            if func.is_private():
                # We have to generate a Viper method to check the specification
                # if the specification of the function could get assumed.
                return self.function_translator.can_assume_private_function(func)
            return True
        vyper_functions = filter(translate_condition_for_vyper_function, vyper_program.functions.values())
        methods.append(self._create_transitivity_check(ctx))
        methods.append(self._create_reflexivity_check(ctx))
        methods.append(self._create_forced_ether_check(ctx))
        methods += [self.function_translator.translate(function, ctx) for function in vyper_functions]

        for i, t in enumerate(self.viper_ast.seq_types):
            type_vars = { self.viper_ast.TypeVar('$E') : t }
            dt = self.viper_ast.DomainType('_array_ce_helper', type_vars, type_vars.keys())
            functions.append(self.viper_ast.Function('___dummy' + str(i), [], dt, [], [], None))

        # Viper Program
        viper_program = self.viper_ast.Program(domains, [], functions, predicates, methods)
        return viper_program

    def _translate_struct(self, struct: VyperStruct, ctx: Context):
        # For structs we need to synthesize an initializer and an equality domain function with
        # their corresponding axioms
        domain = mangled.struct_name(struct.name, struct.type.kind)
        struct_type = self.type_translator.translate(struct.type, ctx)
        address_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)

        number_of_members = len(struct.type.member_types)
        members = [None] * number_of_members
        for name, vyper_type in struct.type.member_types.items():
            idx = struct.type.member_indices[name]
            member_type = self.type_translator.translate(vyper_type, ctx)
            var_decl = self.viper_ast.LocalVarDecl(f'$arg_{idx}', member_type)
            members[idx] = (name, var_decl)

        init_name = mangled.struct_init_name(struct.name, struct.type.kind)
        init_parms = [var for _, var in members]
        resource_address_var = None
        if isinstance(struct, Resource) and not (struct.name == mangled.CREATOR or struct.name == names.UNDERLYING_WEI):
            # First argument has to be an address for resources if it is not the creator resource
            resource_address_var = self.viper_ast.LocalVarDecl(f'$address_arg', address_type)
            init_parms.append(resource_address_var)
        init_f = self.viper_ast.DomainFunc(init_name, init_parms, struct_type, False, domain)

        eq_name = mangled.struct_eq_name(struct.name, struct.type.kind)
        eq_left_decl = self.viper_ast.LocalVarDecl('$l', struct_type)
        eq_right_decl = self.viper_ast.LocalVarDecl('$r', struct_type)
        eq_parms = [eq_left_decl, eq_right_decl]
        eq_f = self.viper_ast.DomainFunc(eq_name, eq_parms, self.viper_ast.Bool, False, domain)

        init_args = [param.localVar() for param in init_parms]
        init = helpers.struct_init(self.viper_ast, init_args, struct.type)
        # The type tag of the initializer is always the type tag of the struct being initialized
        type_tag = self.viper_ast.IntLit(mangled.struct_type_tag(struct.type.name, struct.type.kind))
        init_expr = self.viper_ast.EqCmp(helpers.struct_type_tag(self.viper_ast, init), type_tag)

        eq_left = eq_left_decl.localVar()
        eq_right = eq_right_decl.localVar()
        eq = helpers.struct_eq(self.viper_ast, eq_left, eq_right, struct.type)
        # For two struct to be equal the type tags have to agree, i.e., they have to be of the same Vyper type
        ltag = helpers.struct_type_tag(self.viper_ast, eq_left)
        rtag = helpers.struct_type_tag(self.viper_ast, eq_right)
        eq_expr = self.viper_ast.EqCmp(ltag, rtag)

        for name, var in members:
            init_get = helpers.struct_get(self.viper_ast, init, name, var.typ(), struct.type)
            init_eq = self.viper_ast.EqCmp(init_get, var.localVar())
            init_expr = self.viper_ast.And(init_expr, init_eq)

            eq_get_l = helpers.struct_get(self.viper_ast, eq_left, name, var.typ(), struct.type)
            eq_get_r = helpers.struct_get(self.viper_ast, eq_right, name, var.typ(), struct.type)
            member_type = struct.type.member_types[name]
            eq_eq = self.type_translator.eq(eq_get_l, eq_get_r, member_type, ctx)
            eq_expr = self.viper_ast.And(eq_expr, eq_eq)

        if isinstance(struct, Resource) and not (struct.name == mangled.CREATOR or struct.name == names.UNDERLYING_WEI):
            init_get = helpers.struct_get_idx(self.viper_ast, init, number_of_members, address_type)
            init_eq = self.viper_ast.EqCmp(init_get, resource_address_var.localVar())
            init_expr = self.viper_ast.And(init_expr, init_eq)

            eq_get_l = helpers.struct_get_idx(self.viper_ast, eq_left, number_of_members, address_type)
            eq_get_r = helpers.struct_get_idx(self.viper_ast, eq_right, number_of_members, address_type)
            eq_eq = self.type_translator.eq(eq_get_l, eq_get_r, types.VYPER_ADDRESS, ctx)
            eq_expr = self.viper_ast.And(eq_expr, eq_eq)

        init_trigger = self.viper_ast.Trigger([init])
        init_quant = self.viper_ast.Forall(init_parms, [init_trigger], init_expr)
        init_ax_name = mangled.axiom_name(init_name)
        init_axiom = self.viper_ast.DomainAxiom(init_ax_name, init_quant, domain)

        eq_trigger = self.viper_ast.Trigger([eq])
        eq_lr_eq = self.viper_ast.EqCmp(eq_left, eq_right)
        eq_equals = self.viper_ast.EqCmp(eq, eq_lr_eq)
        eq_definition = self.viper_ast.EqCmp(eq, eq_expr)
        eq_expr = self.viper_ast.And(eq_equals, eq_definition)
        eq_quant = self.viper_ast.Forall(eq_parms, [eq_trigger], eq_expr)
        eq_axiom_name = mangled.axiom_name(eq_name)
        eq_axiom = self.viper_ast.DomainAxiom(eq_axiom_name, eq_quant, domain)

        return self.viper_ast.Domain(domain, [init_f, eq_f], [init_axiom, eq_axiom], [])

    def _translate_ghost_function(self, function: GhostFunction, ctx: Context):
        # We translate a ghost function as a function where the first argument is the
        # self struct usually obtained through the contracts map

        pos = self.to_position(function.node, ctx)

        fname = mangled.ghost_function_name(function.interface, function.name)
        addr_var = TranslatedVar(names.ADDRESS, '$addr', types.VYPER_ADDRESS, self.viper_ast, pos)
        self_var = TranslatedVar(names.SELF, '$self', AnyStructType(), self.viper_ast, pos)
        self_address = helpers.self_address(self.viper_ast, pos)
        args = [addr_var, self_var]
        for idx, var in enumerate(function.args.values()):
            args.append(TranslatedVar(var.name, f'$arg_{idx}', var.type, self.viper_ast, pos))
        args_var_decls = [arg.var_decl(ctx) for arg in args]
        viper_type = self.type_translator.translate(function.type.return_type, ctx)

        if ctx.program.config.has_option(names.CONFIG_TRUST_CASTS):
            pres = []
        else:
            ifs = filter(lambda i: function.name in i.ghost_functions, ctx.program.interfaces.values())
            interface = next(ifs)
            addr = addr_var.local_var(ctx)
            implements = helpers.implements(self.viper_ast, addr, interface.name, ctx, pos)
            pres = [implements]

        result = self.viper_ast.Result(viper_type)
        posts = self.type_translator.type_assumptions(result, function.type.return_type, ctx)

        # If the ghost function has an implementation we add a postcondition for that
        implementation = ctx.program.ghost_function_implementations.get(function.name)
        if implementation:
            with ctx.function_scope():
                ctx.args = {arg.name: arg for arg in args}
                ctx.current_state = {mangled.SELF: self_var}
                body = implementation.node.body[0]
                assert isinstance(body, ast.ExprStmt)
                expr = body.value
                stmts = []
                impl_expr = self.specification_translator.translate(expr, stmts, ctx)
                assert not stmts
                definition = self.viper_ast.EqCmp(result, impl_expr, pos)
                # The implementation is only defined for the self address
                is_self = self.viper_ast.EqCmp(addr_var.local_var(ctx), self_address, pos)
                posts.append(self.viper_ast.Implies(is_self, definition, pos))

        return self.viper_ast.Function(fname, args_var_decls, viper_type, pres, posts, None, pos)

    def _translate_implements(self, program: VyperProgram, ctx: Context):
        domain = mangled.IMPLEMENTS_DOMAIN
        self_address = helpers.self_address(self.viper_ast)
        implements = []
        for interface in program.implements:
            implements.append(helpers.implements(self.viper_ast, self_address, interface.name, ctx))

        axiom_name = mangled.axiom_name(domain)
        axiom_body = reduce(self.viper_ast.And, implements, self.viper_ast.TrueLit())
        axiom = self.viper_ast.DomainAxiom(axiom_name, axiom_body, domain)
        return self.viper_ast.Domain(domain, [], [axiom], {})

    def _translate_event(self, event: VyperEvent, ctx: Context):
        name = mangled.event_name(event.name)
        viper_types = [self.type_translator.translate(arg, ctx) for arg in event.type.arg_types]
        args = [self.viper_ast.LocalVarDecl(f'$arg{idx}', viper_type) for idx, viper_type in enumerate(viper_types)]
        return self.viper_ast.Predicate(name, args, None)

    def _translate_accessible(self, function: VyperFunction, ctx: Context):
        name = mangled.accessible_name(function.name)
        arg0 = self.viper_ast.LocalVarDecl('$tag', self.viper_ast.Int)
        address_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
        arg1 = self.viper_ast.LocalVarDecl('$to', address_type)
        wei_value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
        arg2 = self.viper_ast.LocalVarDecl('$amount', wei_value_type)
        args = [arg0, arg1, arg2]
        for idx, arg in enumerate(function.args.values()):
            arg_name = f'$arg{idx}'
            arg_type = self.type_translator.translate(arg.type, ctx)
            args.append(self.viper_ast.LocalVarDecl(arg_name, arg_type))
        return self.viper_ast.Predicate(name, args, None)

    def _assume_assertions(self, self_state: State, old_state: State, res: List[Stmt], ctx: Context):
        with ctx.state_scope(self_state, old_state):
            for inv in ctx.unchecked_invariants():
                res.append(self.viper_ast.Inhale(inv))
            for interface_type in ctx.program.implements:
                interface = ctx.program.interfaces[interface_type.name]
                with ctx.program_scope(interface):
                    for inv in ctx.current_program.invariants:
                        pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        inv_expr = self.specification_translator.translate_invariant(inv, res, ctx)
                        res.append(self.viper_ast.Inhale(inv_expr, pos))
            for inv in ctx.current_program.invariants:
                pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                inv_expr = self.specification_translator.translate_invariant(inv, res, ctx)
                res.append(self.viper_ast.Inhale(inv_expr, pos))
            is_post_var = self.viper_ast.LocalVar('$post', self.viper_ast.Bool)
            for post in ctx.program.transitive_postconditions:
                pos = self.to_position(post, ctx, rules.INHALE_POSTCONDITION_FAIL)
                post_expr = self.specification_translator.translate_pre_or_postcondition(post, res, ctx)
                post_expr = self.viper_ast.Implies(is_post_var, post_expr, pos)
                res.append(self.viper_ast.Inhale(post_expr, pos))
            for post in ctx.unchecked_transitive_postconditions():
                post_expr = self.viper_ast.Implies(is_post_var, post)
                res.append(self.viper_ast.Inhale(post_expr))

    def _create_transitivity_check(self, ctx: Context):
        # Creates a check that all invariants and transitive postconditions are transitive.
        # This is needed, because we want to assume them after a call, which could have
        # reentered multiple times.
        # To check transitivity, we create 3 states, assume the global unchecked invariants
        # for all of them, assume the invariants for state no 1 (with state no 1 being the
        # old state), for state no 2 (with state no 1 being the old state), and again for
        # state no 3 (with state no 2 being the old state).
        # In the end we assert the invariants for state no 3 (with state no 1 being the old state)
        # The transitive postconditions are checked similarly, but conditioned under an unkown
        # boolean variable so we can't assume them for checking the invariants

        with ctx.function_scope():
            name = mangled.TRANSITIVITY_CHECK

            states = [self.state_translator.state(lambda n: f'${n}${i}', ctx) for i in range(3)]

            block = TranslatedVar(names.BLOCK, mangled.BLOCK, types.BLOCK_TYPE, self.viper_ast)
            ctx.locals[names.BLOCK] = block
            is_post = self.viper_ast.LocalVarDecl('$post', self.viper_ast.Bool)
            local_vars = [*flatten(s.values() for s in states), block]
            local_vars = [var.var_decl(ctx) for var in local_vars]
            local_vars.append(is_post)

            if ctx.program.analysis.uses_issued:
                ctx.issued_state = self.state_translator.state(mangled.issued_state_var_name, ctx)
                local_vars.extend(var.var_decl(ctx) for var in ctx.issued_state.values())
                all_states = chain(states, [ctx.issued_state])
            else:
                all_states = states

            body = []

            # Assume type assumptions for all self-states
            for state in all_states:
                for var in state.values():
                    local = var.local_var(ctx)
                    type_assumptions = self.type_translator.type_assumptions(local, var.type, ctx)
                    body.extend(self.viper_ast.Inhale(a) for a in type_assumptions)

            # Assume type assumptions for block
            block_var = block.local_var(ctx)
            block_assumptions = self.type_translator.type_assumptions(block_var, types.BLOCK_TYPE, ctx)
            body.extend(self.viper_ast.Inhale(a) for a in block_assumptions)

            def assume_assertions(s1, s2):
                self._assume_assertions(s1, s2, body, ctx)

            if ctx.program.analysis.uses_issued:
                # Assume assertions for issued state and issued state
                assume_assertions(ctx.issued_state, ctx.issued_state)
                # Assume assertions for current state 0 and issued state
                assume_assertions(states[0], ctx.issued_state)
            else:
                # Assume assertions for current state 0 and old state 0
                assume_assertions(states[0], states[0])

            # Assume assertions for current state 1 and old state 0
            assume_assertions(states[1], states[0])

            # Assume assertions for current state 2 and old state 1
            assume_assertions(states[2], states[1])

            # Check invariants for current state 2 and old state 0
            with ctx.state_scope(states[2], states[0]):
                for interface_type in ctx.program.implements:
                    interface = ctx.program.interfaces[interface_type.name]
                    with ctx.program_scope(interface):
                        for inv in ctx.current_program.invariants:
                            rule = rules.INVARIANT_TRANSITIVITY_VIOLATED
                            apos = self.to_position(inv, ctx, rule)
                            inv_expr = self.specification_translator.translate_invariant(inv, body, ctx)
                            body.append(self.viper_ast.Assert(inv_expr, apos))

                for inv in ctx.current_program.invariants:
                    rule = rules.INVARIANT_TRANSITIVITY_VIOLATED
                    apos = self.to_position(inv, ctx, rule)
                    inv_expr = self.specification_translator.translate_invariant(inv, body, ctx)
                    body.append(self.viper_ast.Assert(inv_expr, apos))

                for post in ctx.program.transitive_postconditions:
                    rule = rules.POSTCONDITION_TRANSITIVITY_VIOLATED
                    apos = self.to_position(post, ctx, rule)
                    post_expr = self.specification_translator.translate_invariant(post, body, ctx)
                    pos = self.to_position(post, ctx)
                    is_post_var = self.viper_ast.LocalVar('$post', self.viper_ast.Bool, pos)
                    post_expr = self.viper_ast.Implies(is_post_var, post_expr, pos)
                    body.append(self.viper_ast.Assert(post_expr, apos))

            local_vars.extend(ctx.new_local_vars)
            return self.viper_ast.Method(name, [], [], [], [], local_vars, body)

    def _create_reflexivity_check(self, ctx: Context):
        # Creates a check that all invariants and transitive postconditions are reflexive.
        # This is needed, because we want to assume them after a call, which could have
        # reentered zero times.
        # To check transitivity, we create 2 states, assume the global unchecked invariants
        # for both of them, assume the invariants for state no 2 with state no 1 being the
        # old state.
        # In the end we assert the invariants for state no 2 with state no 2 being the old state.
        # The transitive postconditions are checked similarly, but conditioned under an unknown
        # boolean variable so we can't assume them for checking the invariants

        with ctx.function_scope():
            name = mangled.REFLEXIVITY_CHECK

            states = [self.state_translator.state(lambda n: f'${n}${i}', ctx) for i in range(2)]

            block = TranslatedVar(names.BLOCK, mangled.BLOCK, types.BLOCK_TYPE, self.viper_ast)
            ctx.locals[names.BLOCK] = block
            is_post = self.viper_ast.LocalVarDecl('$post', self.viper_ast.Bool)
            local_vars = [*flatten(s.values() for s in states), block]
            local_vars = [var.var_decl(ctx) for var in local_vars]
            local_vars.append(is_post)

            if ctx.program.analysis.uses_issued:
                ctx.issued_state = self.state_translator.state(mangled.issued_state_var_name, ctx)
                local_vars.extend(var.var_decl(ctx) for var in ctx.issued_state.values())
                all_states = chain(states, [ctx.issued_state])
            else:
                all_states = states

            body = []

            # Assume type assumptions for all self-states
            for state in all_states:
                for var in state.values():
                    local = var.local_var(ctx)
                    type_assumptions = self.type_translator.type_assumptions(local, var.type, ctx)
                    body.extend(self.viper_ast.Inhale(a) for a in type_assumptions)

            # Assume type assumptions for block
            block_var = block.local_var(ctx)
            block_assumptions = self.type_translator.type_assumptions(block_var, types.BLOCK_TYPE, ctx)
            body.extend(self.viper_ast.Inhale(a) for a in block_assumptions)

            def assume_assertions(s1, s2):
                self._assume_assertions(s1, s2, body, ctx)

            # Assume assertions for current state 1 and old state 0
            assume_assertions(states[1], states[0])

            # Check invariants for current state 1 and old state 1
            with ctx.state_scope(states[1], states[1]):
                for inv in ctx.program.invariants:
                    rule = rules.INVARIANT_REFLEXIVITY_VIOLATED
                    apos = self.to_position(inv, ctx, rule)
                    inv_expr = self.specification_translator.translate_invariant(inv, body, ctx)
                    body.append(self.viper_ast.Assert(inv_expr, apos))

                for post in ctx.program.transitive_postconditions:
                    rule = rules.POSTCONDITION_REFLEXIVITY_VIOLATED
                    apos = self.to_position(post, ctx, rule)
                    post_expr = self.specification_translator.translate_invariant(post, body, ctx)
                    pos = self.to_position(post, ctx)
                    is_post_var = self.viper_ast.LocalVar('$post', self.viper_ast.Bool, pos)
                    post_expr = self.viper_ast.Implies(is_post_var, post_expr, pos)
                    body.append(self.viper_ast.Assert(post_expr, apos))

            local_vars.extend(ctx.new_local_vars)
            return self.viper_ast.Method(name, [], [], [], [], local_vars, body)

    def _create_forced_ether_check(self, ctx: Context):
        # Creates a check that all transitive postconditions still hold after
        # forcibly receiving ether through selfdestruct or coinbase transactions

        with ctx.function_scope():
            name = mangled.FORCED_ETHER_CHECK

            present_state = self.state_translator.state(mangled.present_state_var_name, ctx)
            pre_state = self.state_translator.state(mangled.pre_state_var_name, ctx)

            local_vars = [var.var_decl(ctx) for var in chain(present_state.values(), pre_state.values())]

            if ctx.program.analysis.uses_issued:
                issued_state = self.state_translator.state(mangled.issued_state_var_name, ctx)
                ctx.issued_state = issued_state
                local_vars.extend(var.var_decl(ctx) for var in issued_state.values())

                all_states = [present_state, pre_state, issued_state]
            else:
                all_states = [present_state, pre_state]

            block = TranslatedVar(names.BLOCK, mangled.BLOCK, types.BLOCK_TYPE, self.viper_ast)
            ctx.locals[names.BLOCK] = block
            is_post = self.viper_ast.LocalVarDecl('$post', self.viper_ast.Bool)
            havoc = self.viper_ast.LocalVarDecl('$havoc', self.viper_ast.Int)
            local_vars.extend([is_post, havoc, block.var_decl(ctx)])

            body = []

            for state in all_states:
                for var in state.values():
                    local = var.local_var(ctx)
                    type_assumptions = self.type_translator.type_assumptions(local, var.type, ctx)
                    body.extend(self.viper_ast.Inhale(a) for a in type_assumptions)

            # Assume type assumptions for block
            block_var = block.local_var(ctx)
            block_assumptions = self.type_translator.type_assumptions(block_var, types.BLOCK_TYPE, ctx)
            body.extend(self.viper_ast.Inhale(a) for a in block_assumptions)

            def assume_assertions(s1, s2):
                self._assume_assertions(s1, s2, body, ctx)

            # Assume balance increase to be non-negative
            zero = self.viper_ast.IntLit(0)
            assume_non_negative = self.viper_ast.Inhale(self.viper_ast.GeCmp(havoc.localVar(), zero))
            body.append(assume_non_negative)

            if ctx.program.analysis.uses_issued:
                assume_assertions(issued_state, issued_state)
                assume_assertions(present_state, issued_state)
            else:
                assume_assertions(present_state, present_state)

            self.state_translator.copy_state(present_state, pre_state, body, ctx)

            with ctx.state_scope(present_state, present_state):
                self.balance_translator.increase_balance(havoc.localVar(), body, ctx)

            with ctx.state_scope(present_state, pre_state):
                for post in ctx.program.transitive_postconditions:
                    rule = rules.POSTCONDITION_CONSTANT_BALANCE
                    apos = self.to_position(post, ctx, rule)
                    post_expr = self.specification_translator.translate_pre_or_postcondition(post, body, ctx)
                    pos = self.to_position(post, ctx)
                    is_post_var = self.viper_ast.LocalVar('$post', self.viper_ast.Bool, pos)
                    post_expr = self.viper_ast.Implies(is_post_var, post_expr, pos)
                    body.append(self.viper_ast.Assert(post_expr, apos))

            local_vars.extend(ctx.new_local_vars)
            return self.viper_ast.Method(name, [], [], [], [], local_vars, body)
