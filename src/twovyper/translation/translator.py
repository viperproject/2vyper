"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.utils import seq_to_list

from twovyper.ast import names
from twovyper.ast import types
from twovyper.ast.nodes import VyperProgram, VyperEvent, VyperStruct, VyperFunction

from twovyper.viper.typedefs import Program, Stmt, Expr
from twovyper.viper.ast import ViperAST

from twovyper.translation.abstract import PositionTranslator
from twovyper.translation.function import FunctionTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.specification import SpecificationTranslator
from twovyper.translation.balance import BalanceTranslator
from twovyper.translation.context import Context, function_scope, self_scope

from twovyper.translation import mangled
from twovyper.translation import helpers

from twovyper.verification import rules


class ProgramTranslator(PositionTranslator):

    def __init__(self, viper_ast: ViperAST, builtins: Program):
        self.viper_ast = viper_ast
        self.builtins = builtins
        self.function_translator = FunctionTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)
        self.balance_translator = BalanceTranslator(viper_ast)

    def translate(self, vyper_program: VyperProgram, file: str) -> Program:
        if names.INIT not in vyper_program.functions:
            vyper_program.functions[mangled.INIT] = helpers.init_function()

        # Add built-in methods
        methods = seq_to_list(self.builtins.methods())
        # Add built-in domains
        domains = seq_to_list(self.builtins.domains())
        # Add built-in functions
        functions = seq_to_list(self.builtins.functions())

        # Add self.$sent field
        sent_type = types.MapType(types.VYPER_ADDRESS, types.VYPER_WEI_VALUE)
        vyper_program.fields.type.add_member(mangled.SENT_FIELD, sent_type)
        # Add self.$received field
        received_type = types.MapType(types.VYPER_ADDRESS, types.VYPER_WEI_VALUE)
        vyper_program.fields.type.add_member(mangled.RECEIVED_FIELD, received_type)

        ctx = Context()
        ctx.file = file
        ctx.program = vyper_program

        # Translate self
        domains.append(self._translate_struct(vyper_program.fields, ctx))

        for field, field_type in vyper_program.fields.type.member_types.items():
            ctx.field_types[field] = self.type_translator.translate(field_type, ctx)

        def unchecked_invariants():
            self_var = ctx.self_var.localVar()
            old_self_var = ctx.old_self_var.localVar()
            address_type = self.type_translator.translate(types.VYPER_ADDRESS, ctx)
            q_var = self.viper_ast.LocalVarDecl('$a', address_type)
            q_local = q_var.localVar()
            sent = self.balance_translator.get_sent(self_var, q_local, ctx)
            old_sent = self.balance_translator.get_sent(old_self_var, q_local, ctx)
            expr = self.viper_ast.GeCmp(sent, old_sent)
            trigger = self.viper_ast.Trigger([sent])
            return [self.viper_ast.Forall([q_var], [trigger], expr)]

        ctx.unchecked_invariants = unchecked_invariants

        # Structs
        structs = vyper_program.structs.values()
        domains.extend(self._translate_struct(struct, ctx) for struct in structs)

        # Events
        events = [self._translate_event(event, ctx) for event in vyper_program.events.values()]
        accs = [self._translate_accessible(acc, ctx) for acc in vyper_program.functions.values()]
        predicates = [*events, *accs]

        vyper_functions = [f for f in vyper_program.functions.values() if f.is_public()]
        methods.append(self._create_transitivity_check(ctx))
        methods.append(self._create_forced_ether_check(ctx))
        methods += [self.function_translator.translate(function, ctx) for function in vyper_functions]
        viper_program = self.viper_ast.Program(domains, [], functions, predicates, methods)
        return viper_program

    def _translate_struct(self, struct: VyperStruct, ctx: Context):
        # For structs we need to synthesize an initializer and and equality domain function and
        # their corresponding axioms
        domain = mangled.struct_name(struct.name)
        struct_type = self.type_translator.translate(struct.type, ctx)

        members = [None] * len(struct.type.member_types)
        for name, type in struct.type.member_types.items():
            idx = struct.type.member_indices[name]
            member_type = self.type_translator.translate(type, ctx)
            var_decl = self.viper_ast.LocalVarDecl(f'$arg_{idx}', member_type)
            members[idx] = (name, var_decl)

        init_name = mangled.struct_init_name(struct.name)
        init_parms = [var for _, var in members]
        init_f = self.viper_ast.DomainFunc(init_name, init_parms, struct_type, False, domain)

        eq_name = mangled.struct_eq_name(struct.name)
        eq_left_decl = self.viper_ast.LocalVarDecl('$l', struct_type)
        eq_right_decl = self.viper_ast.LocalVarDecl('$r', struct_type)
        eq_parms = [eq_left_decl, eq_right_decl]
        eq_f = self.viper_ast.DomainFunc(eq_name, eq_parms, self.viper_ast.Bool, False, domain)

        init_args = [param.localVar() for param in init_parms]
        init = helpers.struct_init(self.viper_ast, init_args, struct.type)
        init_expr = self.viper_ast.TrueLit()

        eq_left = eq_left_decl.localVar()
        eq_right = eq_right_decl.localVar()
        eq = helpers.struct_eq(self.viper_ast, eq_left, eq_right, struct.type)
        eq_expr = self.viper_ast.TrueLit()

        for name, var in members:
            init_get = helpers.struct_get(self.viper_ast, init, name, var.typ(), struct.type)
            init_eq = self.viper_ast.EqCmp(init_get, var.localVar())
            init_expr = self.viper_ast.And(init_expr, init_eq)

            eq_get_l = helpers.struct_get(self.viper_ast, eq_left, name, var.typ(), struct.type)
            eq_get_r = helpers.struct_get(self.viper_ast, eq_right, name, var.typ(), struct.type)
            member_type = struct.type.member_types[name]
            eq_eq = self.type_translator.eq(None, eq_get_l, eq_get_r, member_type, ctx)
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

    def _translate_event(self, event: VyperEvent, ctx: Context):
        name = mangled.event_name(event.name)
        types = [self.type_translator.translate(arg, ctx) for arg in event.type.arg_types]
        args = [self.viper_ast.LocalVarDecl(f'$arg{idx}', type) for idx, type in enumerate(types)]
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

    def _assume_assertions(self, self_state: Expr, old_state: Expr, ctx: Context) -> List[Stmt]:
        body = []
        with self_scope(self_state, old_state, ctx):
            for inv in ctx.unchecked_invariants():
                body.append(self.viper_ast.Inhale(inv))
            for inv in ctx.program.invariants:
                pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                inv_expr = self.specification_translator.translate_invariant(inv, ctx)
                body.append(self.viper_ast.Inhale(inv_expr, pos))
            for post in ctx.program.transitive_postconditions:
                pos = self.to_position(post, ctx, rules.INHALE_POSTCONDITION_FAIL)
                # We translate the postcondition like an invariant because we don't
                # want old to refer to the pre state
                post_expr = self.specification_translator.translate_invariant(post, ctx)
                is_post_var = self.viper_ast.LocalVar('$post', self.viper_ast.Bool, pos)
                post_expr = self.viper_ast.Implies(is_post_var, post_expr, pos)
                body.append(self.viper_ast.Inhale(post_expr, pos))
        return body

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

        with function_scope(ctx):
            name = mangled.TRANSITIVITY_CHECK

            self_type = self.type_translator.translate(ctx.self_type, ctx)
            states = [self.viper_ast.LocalVarDecl(f'$s{i}', self_type) for i in range(3)]

            block_type = self.type_translator.translate(types.BLOCK_TYPE, ctx)
            block = self.viper_ast.LocalVarDecl(mangled.BLOCK, block_type)
            ctx.all_vars[names.BLOCK] = block
            is_post = self.viper_ast.LocalVarDecl('$post', self.viper_ast.Bool)
            local_vars = [*states, block, is_post]

            body = []

            def assume_assertions(s1, s2):
                body.extend(self._assume_assertions(s1, s2, ctx))

            # Assume type assumptions for all self-states
            for state in states:
                var = state.localVar()
                type_assumptions = self.type_translator.type_assumptions(var, ctx.self_type, ctx)
                body.extend(self.viper_ast.Inhale(a) for a in type_assumptions)

            # Assume type assumptions for block
            block_var = block.localVar()
            block_assumptions = self.type_translator.type_assumptions(block_var, types.BLOCK_TYPE, ctx)
            body.extend(self.viper_ast.Inhale(a) for a in block_assumptions)

            # Assume assertions for current state 0 and old state 0
            assume_assertions(states[0], states[0])

            # Assume assertions for current state 1 and old state 0
            assume_assertions(states[1], states[0])

            # Assume assertions for current state 2 and old state 1
            assume_assertions(states[2], states[1])

            # Check invariants for current state 2 and old state 0
            with self_scope(states[2], states[0], ctx):
                for inv in ctx.program.invariants:
                    rule = rules.INVARIANT_TRANSITIVITY_VIOLATED
                    apos = self.to_position(inv, ctx, rule)
                    inv_expr = self.specification_translator.translate_invariant(inv, ctx)
                    body.append(self.viper_ast.Assert(inv_expr, apos))

                for post in ctx.program.transitive_postconditions:
                    rule = rules.POSTCONDITION_TRANSITIVITY_VIOLATED
                    apos = self.to_position(post, ctx, rule)
                    post_expr = self.specification_translator.translate_invariant(post, ctx)
                    pos = self.to_position(post, ctx)
                    is_post_var = self.viper_ast.LocalVar('$post', self.viper_ast.Bool, pos)
                    post_expr = self.viper_ast.Implies(is_post_var, post_expr, pos)
                    body.append(self.viper_ast.Assert(post_expr, apos))

            return self.viper_ast.Method(name, [], [], [], [], local_vars, body)

    def _create_forced_ether_check(self, ctx: Context):
        # Creates a check that all transitive postconditions still hold after
        # forcibly receiving ether through selfdestruct or coinbase transactions

        with function_scope(ctx):
            name = mangled.FORCED_ETHER_CHECK

            self_type = self.type_translator.translate(ctx.self_type, ctx)
            self_var = helpers.self_var(self.viper_ast, self_type)
            self_local = self_var.localVar()
            pre_self_var = helpers.pre_self_var(self.viper_ast, self_type)
            pre_self_local = pre_self_var.localVar()

            block_type = self.type_translator.translate(types.BLOCK_TYPE, ctx)
            block = self.viper_ast.LocalVarDecl(mangled.BLOCK, block_type)
            ctx.all_vars[names.BLOCK] = block
            is_post = self.viper_ast.LocalVarDecl('$post', self.viper_ast.Bool)
            havoc = self.viper_ast.LocalVarDecl('$havoc', self.viper_ast.Int)
            local_vars = [self_var, pre_self_var, block, is_post, havoc]

            body = []

            def assume_assertions(s1, s2):
                body.extend(self._assume_assertions(s1, s2, ctx))

            # Assume type assumptions for self
            type_assumptions = self.type_translator.type_assumptions(self_local, ctx.self_type, ctx)
            body.extend([self.viper_ast.Inhale(a) for a in type_assumptions])

            # Assume type assumptions for block
            block_var = block.localVar()
            block_assumptions = self.type_translator.type_assumptions(block_var, types.BLOCK_TYPE, ctx)
            body.extend(self.viper_ast.Inhale(a) for a in block_assumptions)

            # Assume balance increase to be non-negative
            zero = self.viper_ast.IntLit(0)
            assume_non_negative = self.viper_ast.Inhale(self.viper_ast.GeCmp(havoc.localVar(), zero))
            body.append(assume_non_negative)

            assume_assertions(self_var, self_var)

            body.append(self.viper_ast.LocalVarAssign(pre_self_local, self_local))

            with self_scope(self_var, self_var, ctx):
                body.append(self.balance_translator.increase_balance(havoc.localVar(), ctx))

            with self_scope(self_var, pre_self_var, ctx):
                for post in ctx.program.transitive_postconditions:
                    rule = rules.POSTCONDITION_CONSTANT_BALANCE
                    apos = self.to_position(post, ctx, rule)
                    post_expr = self.specification_translator.translate_invariant(post, ctx)
                    pos = self.to_position(post, ctx)
                    is_post_var = self.viper_ast.LocalVar('$post', self.viper_ast.Bool, pos)
                    post_expr = self.viper_ast.Implies(is_post_var, post_expr, pos)
                    body.append(self.viper_ast.Assert(post_expr, apos))

            return self.viper_ast.Method(name, [], [], [], [], local_vars, body)
