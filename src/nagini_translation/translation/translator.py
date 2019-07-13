"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from nagini_translation.utils import seq_to_list

from nagini_translation.ast import names
from nagini_translation.ast import types
from nagini_translation.ast.nodes import VyperProgram, VyperEvent, VyperStruct, VyperVar

from nagini_translation.translation.abstract import PositionTranslator
from nagini_translation.translation.function import FunctionTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.specification import SpecificationTranslator
from nagini_translation.translation.context import Context, old_label_scope, function_scope

from nagini_translation.translation import builtins

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
            vyper_program.functions[builtins.INIT] = builtins.init_function()

        # Add self.balance field
        balance_var = VyperVar(names.SELF_BALANCE, types.VYPER_WEI_VALUE, None)
        vyper_program.state[balance_var.name] = balance_var
        # Add self.$sent field
        sent_type = types.MapType(types.VYPER_ADDRESS, types.VYPER_WEI_VALUE)
        sent_var = VyperVar(builtins.SENT_FIELD, sent_type, None)
        vyper_program.state[sent_var.name] = sent_var
        # Add self.$received field
        received_type = types.MapType(types.VYPER_ADDRESS, types.VYPER_WEI_VALUE)
        received_var = VyperVar(builtins.RECEIVED_FIELD, received_type, None)
        vyper_program.state[received_var.name] = received_var

        # Add built-in methods
        methods = seq_to_list(self.builtins.methods())
        # Add built-in domains
        domains = seq_to_list(self.builtins.domains())
        # Add built-in functions
        functions = seq_to_list(self.builtins.functions())

        ctx = Context(file)
        ctx.program = vyper_program
        ctx.all_vars[names.SELF] = builtins.self_var(self.viper_ast)
        ctx.all_vars[names.MSG] = builtins.msg_var(self.viper_ast)
        ctx.all_vars[names.BLOCK] = builtins.block_var(self.viper_ast)

        ctx.fields = {}
        ctx.permissions = []
        ctx.global_unchecked_invariants = []
        for var in vyper_program.state.values():
            # Create field
            field = self._translate_field(var, ctx)
            ctx.fields[var.name] = field

            # Pass around the permissions for all fields
            field_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), field)
            acc = self._create_field_access_predicate(field_acc, 1, ctx)
            ctx.permissions.append(acc)

            non_negs = self.type_translator.non_negative(field_acc, var.type, ctx)
            ctx.global_unchecked_invariants.extend(non_negs)

            array_lens = self.type_translator.array_length(field_acc, var.type, ctx)
            ctx.global_unchecked_invariants.extend(array_lens)

        ctx.local_unchecked_invariants = []
        ctx.immutable_fields = {}
        ctx.immutable_permissions = []
        # Create msg.sender field
        msg_sender = builtins.msg_sender_field(self.viper_ast)
        ctx.immutable_fields[names.MSG_SENDER] = msg_sender
        # Pass around the permissions for msg.sender
        sender_acc = self.viper_ast.FieldAccess(ctx.msg_var.localVar(), msg_sender)
        acc = self._create_field_access_predicate(sender_acc, 0, ctx)
        ctx.immutable_permissions.append(acc)
        # Assume msg.sender != 0
        zero = self.viper_ast.IntLit(0)
        ctx.local_unchecked_invariants.append(self.viper_ast.NeCmp(sender_acc, zero))

        # Create msg.value field
        msg_value = builtins.msg_value_field(self.viper_ast)
        ctx.immutable_fields[names.MSG_VALUE] = msg_value
        # Pass around the permissions for msg.value
        value_acc = self.viper_ast.FieldAccess(ctx.msg_var.localVar(), msg_value)
        acc = self._create_field_access_predicate(value_acc, 0, ctx)
        ctx.immutable_permissions.append(acc)
        # Assume msg.value >= 0
        ctx.local_unchecked_invariants.append(self.viper_ast.GeCmp(value_acc, zero))

        # Create block.timestamp field
        block_timestamp = builtins.block_timestamp_field(self.viper_ast)
        ctx.immutable_fields[names.BLOCK_TIMESTAMP] = block_timestamp
        # Pass around the permissions for block.timestamp
        timestamp_acc = self.viper_ast.FieldAccess(ctx.block_var.localVar(), block_timestamp)
        acc = self._create_field_access_predicate(timestamp_acc, 1, ctx)
        ctx.immutable_permissions.append(acc)
        # Assume block.timestamp >= 0
        ctx.local_unchecked_invariants.append(self.viper_ast.GeCmp(timestamp_acc, zero))

        fields_list = [*ctx.fields.values(), *ctx.immutable_fields.values()]

        # Structs
        for struct in vyper_program.structs.values():
            domains.append(self._translate_struct(struct, ctx))

        # Events
        predicates = [self._translate_event(event, ctx) for event in vyper_program.events.values()]

        vyper_functions = [f for f in vyper_program.functions.values() if f.is_public()]
        methods.append(self._create_transitivity_check(ctx))
        methods += [self.function_translator.translate(function, ctx) for function in vyper_functions]
        viper_program = self.viper_ast.Program(domains, fields_list, functions, predicates, methods)
        return viper_program

    def _translate_field(self, var: VyperVar, ctx: Context):
        pos = self.to_position(var.node, ctx)

        name = builtins.field_name(var.name)
        type = self.type_translator.translate(var.type, ctx)
        field = self.viper_ast.Field(name, type, pos)

        return field

    def _translate_struct(self, struct: VyperStruct, ctx: Context):
        viper_int = self.viper_ast.Int
        struct_name = builtins.struct_name(struct.name)
        struct_type = self.type_translator.translate(struct.type, ctx)

        struct_var = self.viper_ast.LocalVarDecl('$s', struct_type)
        field_var = self.viper_ast.LocalVarDecl('$f', viper_int)

        fields_function_name = builtins.struct_field_name(struct.name)
        fields_function = self.viper_ast.DomainFunc(fields_function_name, [struct_var, field_var], viper_int, False, struct_name)

        functions = [fields_function]
        axioms = []
        for name, type in struct.type.arg_types.items():
            member_type = self.type_translator.translate(type, ctx)

            getter_name = builtins.struct_member_getter_name(struct.name, name)
            functions.append(self.viper_ast.DomainFunc(getter_name, [field_var], member_type, False, struct_name))

            setter_name = builtins.struct_member_setter_name(struct.name, name)
            new_var = self.viper_ast.LocalVarDecl('$v', member_type)
            functions.append(self.viper_ast.DomainFunc(setter_name, [struct_var, new_var], struct_type, False, struct_name))

            set_ax_name = builtins.axiom_name(f'{setter_name}_0')
            local_s = struct_var.localVar()
            local_v = new_var.localVar()
            set_m = builtins.struct_set(self.viper_ast, local_s, local_v, name, struct.type)
            get_m = builtins.struct_get(self.viper_ast, set_m, name, member_type, struct.type)
            eq = self.viper_ast.EqCmp(get_m, local_v)
            trigger = self.viper_ast.Trigger([get_m])
            quant = self.viper_ast.Forall([struct_var, new_var], [trigger], eq)
            axioms.append(self.viper_ast.DomainAxiom(set_ax_name, quant, struct_name))

            set_ax_name = builtins.axiom_name(f'{setter_name}_1')
            local_f = field_var.localVar()
            idx = self.viper_ast.IntLit(struct.type.arg_indices[name])
            neq = self.viper_ast.NeCmp(local_f, idx)
            field_v_f = builtins.struct_field(self.viper_ast, local_s, local_f, struct.type)
            field_set_f = builtins.struct_field(self.viper_ast, set_m, local_f, struct.type)
            impl = self.viper_ast.Implies(neq, self.viper_ast.EqCmp(field_v_f, field_set_f))
            trigger = self.viper_ast.Trigger([field_set_f])
            quant = self.viper_ast.Forall([struct_var, new_var, field_var], [trigger], impl)
            axioms.append(self.viper_ast.DomainAxiom(set_ax_name, quant, struct_name))

        return self.viper_ast.Domain(struct_name, functions, axioms, [])

    def _translate_event(self, event: VyperEvent, ctx: Context):
        name = builtins.event_name(event.name)
        types = [self.type_translator.translate(arg, ctx) for arg in event.type.arg_types]
        args = [self.viper_ast.LocalVarDecl(f'$arg{idx}', type) for idx, type in enumerate(types)]
        return self.viper_ast.Predicate(name, args, None)

    def _create_field_access_predicate(self, field_access, amount, ctx: Context):
        if amount == 1:
            perm = self.viper_ast.FullPerm()
        else:
            perm = builtins.read_perm(self.viper_ast)
        return self.viper_ast.FieldAccessPredicate(field_access, perm)

    def _create_transitivity_check(self, ctx: Context):
        # Creates a check that all invariants are transitive. This is needed, because we
        # want to assume the invariant after a call, which could have reentered multiple
        # times.
        # To check transitivity, we create 3 states, assume the global unchecked invariants
        # for all of them, assume the invariants for state no 2 (with state no 1 being the
        # old state), and again for state no 3 (with state no 2 being the old state). In the
        # end we assert the invariants for state no 3 (with state no 1 being the old state)

        with function_scope(ctx):
            name = builtins.TRANSITIVITY_CHECK

            ctx.all_vars[names.SELF] = builtins.self_var(self.viper_ast)

            inhales = [self.viper_ast.Inhale(p) for p in ctx.permissions]
            exhales = [self.viper_ast.Exhale(p) for p in ctx.permissions]

            locals = [builtins.self_var(self.viper_ast)]
            body = []
            body.extend(inhales)
            for inv in ctx.global_unchecked_invariants:
                body.append(self.viper_ast.Inhale(inv))

            old1 = self.viper_ast.Label('$old1')
            body.append(old1)

            body.extend(exhales)
            body.extend(inhales)

            inv1_assumptions = []
            for inv in ctx.global_unchecked_invariants:
                inv1_assumptions.append(self.viper_ast.Inhale(inv))

            with old_label_scope(old1, ctx):
                for inv in ctx.program.invariants:
                    pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                    inv_expr = self.specification_translator.translate_invariant(inv, ctx)
                    inv1_assumptions.append(self.viper_ast.Inhale(inv_expr, pos))

            body.extend(inv1_assumptions)

            old2 = self.viper_ast.Label('$old2')
            body.append(old2)

            body.extend(exhales)
            body.extend(inhales)

            inv2_assumptions = []
            for inv in ctx.global_unchecked_invariants:
                inv2_assumptions.append(self.viper_ast.Inhale(inv))

            with old_label_scope(old2, ctx):
                for inv in ctx.program.invariants:
                    pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                    inv_expr = self.specification_translator.translate_invariant(inv, ctx)
                    inv2_assumptions.append(self.viper_ast.Inhale(inv_expr, pos))

            body.extend(inv2_assumptions)

            inv_assertions = []
            with old_label_scope(old1, ctx):
                for inv in ctx.program.invariants:
                    rule = rules.TRANSITIVITY_VIOLATED
                    apos = self.to_position(inv, ctx, rule)
                    inv_expr = self.specification_translator.translate_invariant(inv, ctx)
                    inv_assertions.append(self.viper_ast.Assert(inv_expr, apos))

            body.extend(inv_assertions)

            return self.viper_ast.Method(name, [], [], [], [], locals, body)
