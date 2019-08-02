"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from nagini_translation.utils import seq_to_list

from nagini_translation.ast import names
from nagini_translation.ast import types
from nagini_translation.ast.nodes import VyperProgram, VyperEvent, VyperStruct, VyperFunction

from nagini_translation.translation.abstract import PositionTranslator
from nagini_translation.translation.function import FunctionTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.specification import SpecificationTranslator
from nagini_translation.translation.context import Context, function_scope, self_scope

from nagini_translation.translation import mangled
from nagini_translation.translation import helpers

from nagini_translation.viper.typedefs import Program
from nagini_translation.viper.ast import ViperAST
from nagini_translation.verification import rules


class ProgramTranslator(PositionTranslator):

    def __init__(self, viper_ast: ViperAST, builtins: Program):
        self.viper_ast = viper_ast
        self.builtins = builtins
        self.function_translator = FunctionTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)

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

        ctx = Context(file)
        ctx.program = vyper_program
        ctx.all_vars[names.SELF] = helpers.self_var(self.viper_ast, ctx.self_type)

        # Translate self
        self_domain = self._translate_struct(vyper_program.fields, ctx)
        domains.append(self_domain)
        self_var = ctx.self_var.localVar()

        for field, field_type in vyper_program.fields.type.member_types.items():
            ctx.field_types[field] = self.type_translator.translate(field_type, ctx)

        ctx.unchecked_invariants = self.type_translator.type_assumptions(self_var, ctx.self_type, ctx)

        # Structs
        for struct in vyper_program.structs.values():
            domains.append(self._translate_struct(struct, ctx))

        # Events
        events = [self._translate_event(event, ctx) for event in vyper_program.events.values()]
        accs = [self._translate_accessible(acc, ctx) for acc in vyper_program.functions.values()]
        predicates = [*events, *accs]

        vyper_functions = [f for f in vyper_program.functions.values() if f.is_public()]
        methods.append(self._create_transitivity_check(ctx))
        methods += [self.function_translator.translate(function, ctx) for function in vyper_functions]
        viper_program = self.viper_ast.Program(domains, [], functions, predicates, methods)
        return viper_program

    def _translate_struct(self, struct: VyperStruct, ctx: Context):
        viper_int = self.viper_ast.Int
        struct_name = mangled.struct_name(struct.name)
        struct_type = self.type_translator.translate(struct.type, ctx)

        struct_var = self.viper_ast.LocalVarDecl('$s', struct_type)
        field_var = self.viper_ast.LocalVarDecl('$f', viper_int)

        fields_function_name = mangled.struct_field_name(struct.name)
        fields_function = self.viper_ast.DomainFunc(fields_function_name, [struct_var, field_var], viper_int, False, struct_name)

        functions = [fields_function]
        axioms = []
        init_args = {}
        init_get = {}
        for name, type in struct.type.member_types.items():
            member_type = self.type_translator.translate(type, ctx)

            getter_name = mangled.struct_member_getter_name(struct.name, name)
            functions.append(self.viper_ast.DomainFunc(getter_name, [field_var], member_type, False, struct_name))

            setter_name = mangled.struct_member_setter_name(struct.name, name)
            new_var = self.viper_ast.LocalVarDecl('$v', member_type)
            functions.append(self.viper_ast.DomainFunc(setter_name, [struct_var, new_var], struct_type, False, struct_name))

            set_ax_name = mangled.axiom_name(f'{setter_name}_0')
            local_s = struct_var.localVar()
            local_v = new_var.localVar()
            set_m = helpers.struct_set(self.viper_ast, local_s, local_v, name, struct.type)
            get_m = helpers.struct_get(self.viper_ast, set_m, name, member_type, struct.type)
            eq = self.viper_ast.EqCmp(get_m, local_v)
            trigger = self.viper_ast.Trigger([get_m])
            quant = self.viper_ast.Forall([struct_var, new_var], [trigger], eq)
            axioms.append(self.viper_ast.DomainAxiom(set_ax_name, quant, struct_name))

            set_ax_name = mangled.axiom_name(f'{setter_name}_1')
            local_f = field_var.localVar()
            idx = struct.type.member_indices[name]
            idx_lit = self.viper_ast.IntLit(idx)
            neq = self.viper_ast.NeCmp(local_f, idx_lit)
            field_v_f = helpers.struct_field(self.viper_ast, local_s, local_f, struct.type)
            field_set_f = helpers.struct_field(self.viper_ast, set_m, local_f, struct.type)
            impl = self.viper_ast.Implies(neq, self.viper_ast.EqCmp(field_v_f, field_set_f))
            trigger = self.viper_ast.Trigger([field_set_f])
            quant = self.viper_ast.Forall([struct_var, new_var, field_var], [trigger], impl)
            axioms.append(self.viper_ast.DomainAxiom(set_ax_name, quant, struct_name))

            init_args[idx] = self.viper_ast.LocalVarDecl(f'arg_{idx}', member_type)

            def ig(s, name=name, member_type=member_type):
                return helpers.struct_get(self.viper_ast, s, name, member_type, struct.type)
            init_get[idx] = ig

        i_args = [init_args[i] for i in range(len(init_args))]
        init_name = mangled.struct_init_name(struct.name)
        init_f = self.viper_ast.DomainFunc(init_name, i_args, struct_type, False, struct_name)
        functions.append(init_f)

        init = helpers.struct_init(self.viper_ast, [arg.localVar() for arg in i_args], struct.type)
        expr = self.viper_ast.TrueLit()
        for i in range(len(init_args)):
            get = init_get[i](init)
            eq = self.viper_ast.EqCmp(get, init_args[i].localVar())
            expr = self.viper_ast.And(expr, eq)

        trigger = self.viper_ast.Trigger([init])
        quant = self.viper_ast.Forall(i_args, [trigger], expr)
        init_ax_name = mangled.axiom_name(init_name)
        axioms.append(self.viper_ast.DomainAxiom(init_ax_name, quant, struct_name))

        return self.viper_ast.Domain(struct_name, functions, axioms, [])

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

    def _create_transitivity_check(self, ctx: Context):
        # Creates a check that all invariants are transitive. This is needed, because we
        # want to assume the invariant after a call, which could have reentered multiple
        # times.
        # To check transitivity, we create 3 states, assume the global unchecked invariants
        # for all of them, assume the invariants for state no 1 (with state no 1 being the
        # old state), for state no 2 (with state no 1 being the old state), and again for
        # state no 3 (with state no 2 being the old state).
        # In the end we assert the invariants for state no 3 (with state no 1 being the old state)

        with function_scope(ctx):
            name = mangled.TRANSITIVITY_CHECK

            self_type = self.type_translator.translate(ctx.self_type, ctx)
            states = [self.viper_ast.LocalVarDecl(f'$s{i}', self_type) for i in range(3)]
            body = []

            # Assume type assumptions for all self-states
            for state in states:
                var = state.localVar()
                type_assumptions = self.type_translator.type_assumptions(var, ctx.self_type, ctx)
                body.extend([self.viper_ast.Inhale(a) for a in type_assumptions])

            def assume_invariants(self_state, old_state):
                with self_scope(self_state, old_state, ctx):
                    for inv in ctx.program.invariants:
                        pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        inv_expr = self.specification_translator.translate_invariant(inv, ctx)
                        body.append(self.viper_ast.Inhale(inv_expr, pos))

            # Assume invariants for current state 0 and old state 0
            assume_invariants(states[0], states[0])

            # Assume invariants for current state 1 and old state 0
            assume_invariants(states[1], states[0])

            # Assume invariants for current state 2 and old state 1
            assume_invariants(states[2], states[1])

            # Check invariants for current state 2 and old state 0
            with self_scope(states[2], states[0], ctx):
                for inv in ctx.program.invariants:
                    rule = rules.TRANSITIVITY_VIOLATED
                    apos = self.to_position(inv, ctx, rule)
                    inv_expr = self.specification_translator.translate_invariant(inv, ctx)
                    body.append(self.viper_ast.Assert(inv_expr, apos))

            return self.viper_ast.Method(name, [], [], [], [], states, body)
