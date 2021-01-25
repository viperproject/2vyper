"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from functools import reduce
from itertools import chain, zip_longest
from typing import List

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.nodes import VyperFunction, VyperVar

from twovyper.translation import helpers, mangled
from twovyper.translation.context import Context
from twovyper.translation.abstract import CommonTranslator
from twovyper.translation.allocation import AllocationTranslator
from twovyper.translation.balance import BalanceTranslator
from twovyper.translation.expression import ExpressionTranslator
from twovyper.translation.model import ModelTranslator
from twovyper.translation.resource import ResourceTranslator
from twovyper.translation.specification import SpecificationTranslator
from twovyper.translation.state import StateTranslator
from twovyper.translation.statement import StatementTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.verification import rules
from twovyper.verification.error import Via

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Method, Stmt, Expr


class FunctionTranslator(CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.allocation_translator = AllocationTranslator(viper_ast)
        self.balance_translator = BalanceTranslator(viper_ast)
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.model_translator = ModelTranslator(viper_ast)
        self.resource_translator = ResourceTranslator(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)
        self.statement_translator = StatementTranslator(viper_ast)
        self.state_translator = StateTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def translate(self, function: VyperFunction, ctx: Context) -> Method:
        with ctx.function_scope():
            # A synthesized __init__ does not have a position in the file
            if function.node:
                pos = self.to_position(function.node, ctx)
            else:
                pos = self.to_position(ctx.program.node, ctx)

            ctx.function = function
            is_init = (function.name == names.INIT)

            do_performs = not ctx.program.config.has_option(names.CONFIG_NO_PERFORMS)

            if is_init and do_performs:
                ctx.program.config.options.append(names.CONFIG_NO_PERFORMS)

            args = {name: self._translate_var(var, ctx, False) for name, var in function.args.items()}
            # Local variables will be added when translating.
            local_vars = {
                # The msg variable
                names.MSG: TranslatedVar(names.MSG, mangled.MSG, types.MSG_TYPE, self.viper_ast),
                # The block variable
                names.BLOCK: TranslatedVar(names.BLOCK, mangled.BLOCK, types.BLOCK_TYPE, self.viper_ast),
                # The chain variable
                names.CHAIN: TranslatedVar(names.CHAIN, mangled.CHAIN, types.CHAIN_TYPE, self.viper_ast),
                # The tx variable
                names.TX: TranslatedVar(names.TX, mangled.TX, types.TX_TYPE, self.viper_ast)
            }

            # We represent self as a struct in each state (present, old, pre, issued).
            # For other contracts we use a map from addresses to structs.

            ctx.present_state = self.state_translator.state(mangled.present_state_var_name, ctx)
            # The last publicly visible state of the blockchain
            ctx.old_state = self.state_translator.state(mangled.old_state_var_name, ctx)
            if function.is_private():
                # The last publicly visible state of the blockchain before the function call
                ctx.pre_old_state = self.state_translator.state(mangled.pre_old_state_var_name, ctx)
            # The state of the blockchain before the function call
            ctx.pre_state = self.state_translator.state(mangled.pre_state_var_name, ctx)
            # The state of the blockchain when the transaction was issued
            ctx.issued_state = self.state_translator.state(mangled.issued_state_var_name, ctx)
            # Usually self refers to the present state and old(self) refers to the old state
            ctx.current_state = ctx.present_state
            ctx.current_old_state = ctx.old_state
            # We create copies of variable maps because ctx is allowed to modify them
            ctx.args = args.copy()
            ctx.locals = local_vars.copy()
            ctx.locals[mangled.ORIGINAL_MSG] = local_vars[names.MSG]

            state_dicts = [ctx.present_state, ctx.old_state, ctx.pre_state, ctx.issued_state]
            if function.is_private():
                state_dicts.append(ctx.pre_old_state)
            state = []
            for d in state_dicts:
                state.extend(d.values())

            self_var = ctx.self_var.local_var(ctx)
            pre_self_var = ctx.pre_self_var.local_var(ctx)

            ctx.success_var = TranslatedVar(names.SUCCESS, mangled.SUCCESS_VAR, types.VYPER_BOOL, self.viper_ast)
            return_variables = [ctx.success_var]
            success_var = ctx.success_var.local_var(ctx)

            end_label = self.viper_ast.Label(mangled.END_LABEL)
            return_label = self.viper_ast.Label(mangled.RETURN_LABEL)
            revert_label = self.viper_ast.Label(mangled.REVERT_LABEL)

            ctx.return_label = mangled.RETURN_LABEL
            ctx.revert_label = mangled.REVERT_LABEL

            if function.type.return_type:
                ctx.result_var = TranslatedVar(names.RESULT, mangled.RESULT_VAR,
                                               function.type.return_type, self.viper_ast)
                return_variables.append(ctx.result_var)

            body = []

            # Assume type assumptions for self state
            self.state_translator.assume_type_assumptions_for_state(ctx.present_state, "Present", body, ctx)
            if function.is_private():
                self.state_translator.assume_type_assumptions_for_state(ctx.old_state, "Old", body, ctx)

            # Assume type assumptions for issued state
            if function.analysis.uses_issued:
                self.state_translator.assume_type_assumptions_for_state(ctx.issued_state, "Issued", body, ctx)

            # Assume type assumptions for self address
            self_address = helpers.self_address(self.viper_ast)
            self_address_ass = self.type_translator.type_assumptions(self_address, types.VYPER_ADDRESS, ctx)
            self_address_assumptions = [self.viper_ast.Inhale(c) for c in self_address_ass]
            self_address_info_msg = "Assume type assumptions for self address"
            self.seqn_with_info(self_address_assumptions, self_address_info_msg, body)

            # Assume type assumptions for arguments
            argument_type_assumptions = []
            for var in function.args.values():
                local_var = args[var.name].local_var(ctx)
                assumptions = self.type_translator.type_assumptions(local_var, var.type, ctx)
                argument_type_assumptions.extend(assumptions)

            argument_cond_assumes = [self.viper_ast.Inhale(c) for c in argument_type_assumptions]
            ui_info_msg = "Assume type assumptions for arguments"
            self.seqn_with_info(argument_cond_assumes, ui_info_msg, body)

            # Assume type assumptions for block
            block_var = ctx.block_var.local_var(ctx)
            block_type_assumptions = self.type_translator.type_assumptions(block_var, types.BLOCK_TYPE, ctx)
            block_assumes = [self.viper_ast.Inhale(c) for c in block_type_assumptions]
            block_info_msg = "Assume type assumptions for block"
            self.seqn_with_info(block_assumes, block_info_msg, body)

            # Assume type assumptions for msg
            msg_var = ctx.msg_var.local_var(ctx)
            msg_type_assumption = self.type_translator.type_assumptions(msg_var, types.MSG_TYPE, ctx)
            # We additionally know that msg.sender != 0
            zero = self.viper_ast.IntLit(0)
            msg_sender = helpers.msg_sender(self.viper_ast, ctx)
            neq0 = self.viper_ast.NeCmp(msg_sender, zero)
            msg_assumes = [self.viper_ast.Inhale(c) for c in chain(msg_type_assumption, [neq0])]
            msg_info_msg = "Assume type assumptions for msg"
            self.seqn_with_info(msg_assumes, msg_info_msg, body)

            # Interface references we have knowledge about and therefore can e.g. assume their invariants
            known_interface_ref = []
            self_type = ctx.program.fields.type
            for member_name, member_type in self_type.member_types.items():
                viper_type = self.type_translator.translate(member_type, ctx)
                if isinstance(member_type, types.InterfaceType):
                    get = helpers.struct_get(self.viper_ast, ctx.self_var.local_var(ctx), member_name,
                                             viper_type, self_type)
                    known_interface_ref.append((member_type.name, get))

            # Assume unchecked and user-specified invariants
            inv_pres_issued = []
            inv_pres_self = []

            # Translate the invariants for the issued state. Since we don't know anything about
            # the state before then, we use the issued state itself as the old state
            if not is_init and function.analysis.uses_issued:
                with ctx.state_scope(ctx.issued_state, ctx.issued_state):
                    for inv in ctx.unchecked_invariants():
                        inv_pres_issued.append(self.viper_ast.Inhale(inv))

                    # Assume implemented interface invariants
                    for interface_type in ctx.program.implements:
                        interface = ctx.program.interfaces[interface_type.name]
                        with ctx.program_scope(interface):
                            for inv in ctx.current_program.invariants:
                                program_pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                                expr = self.specification_translator.translate_invariant(inv, inv_pres_issued,
                                                                                         ctx, True)
                                inv_pres_issued.append(self.viper_ast.Inhale(expr, program_pos))
                    # Assume own invariants
                    for inv in ctx.current_program.invariants:
                        program_pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        expr = self.specification_translator.translate_invariant(inv, inv_pres_issued, ctx, True)
                        inv_pres_issued.append(self.viper_ast.Inhale(expr, program_pos))

            # If we use issued, we translate the invariants for the current state with the
            # issued state as the old state, else we just use the self state as the old state
            # which results in fewer assumptions passed to the prover
            if not is_init:
                present_state = ctx.present_state if function.is_public() else ctx.old_state
                last_state = ctx.issued_state if function.analysis.uses_issued else present_state

                with ctx.state_scope(present_state, last_state):
                    for inv in ctx.unchecked_invariants():
                        inv_pres_self.append(self.viper_ast.Inhale(inv))

                    # Assume implemented interface invariants
                    for interface_type in ctx.program.implements:
                        interface = ctx.program.interfaces[interface_type.name]
                        with ctx.program_scope(interface):
                            for inv in ctx.current_program.invariants:
                                program_pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                                expr = self.specification_translator.translate_invariant(inv, inv_pres_self, ctx)
                                inv_pres_self.append(self.viper_ast.Inhale(expr, program_pos))

                    # Assume own invariants
                    for inv in ctx.current_program.invariants:
                        program_pos = self.to_position(inv, ctx, rules.INHALE_INVARIANT_FAIL)
                        expr = self.specification_translator.translate_invariant(inv, inv_pres_self, ctx)
                        inv_pres_self.append(self.viper_ast.Inhale(expr, program_pos))

                # Also assume the unchecked invariants for non-public states
                if function.is_private():
                    with ctx.state_scope(ctx.present_state, last_state):
                        for inv in ctx.unchecked_invariants():
                            inv_pres_self.append(self.viper_ast.Inhale(inv))

                self.expression_translator.assume_contract_state(known_interface_ref, inv_pres_self, ctx,
                                                                 skip_caller_private=True)
            iv_info_msg = "Assume invariants for issued self"
            self.seqn_with_info(inv_pres_issued, iv_info_msg, body)
            iv_info_msg = "Assume invariants for self"
            self.seqn_with_info(inv_pres_self, iv_info_msg, body)

            if function.is_private():
                # Assume an unspecified permission amount to the events if the function is private
                event_handling = []
                self.expression_translator.log_all_events_zero_or_more_times(event_handling, ctx, pos)
                self.seqn_with_info(event_handling, "Assume we know nothing about events", body)

                # Assume preconditions
                pre_stmts = []
                with ctx.state_scope(ctx.present_state, ctx.old_state):
                    for precondition in function.preconditions:
                        cond = self.specification_translator.\
                            translate_pre_or_postcondition(precondition, pre_stmts, ctx, assume_events=True)
                        pre_pos = self.to_position(precondition, ctx, rules.INHALE_PRECONDITION_FAIL)
                        pre_stmts.append(self.viper_ast.Inhale(cond, pre_pos))

                self.seqn_with_info(pre_stmts, "Assume preconditions", body)

            # pre_self is the same as self in the beginning
            self.state_translator.copy_state(ctx.present_state, ctx.pre_state, body, ctx)
            # If the function is public, old_self is also the same as self in the beginning
            if function.is_public():
                self.state_translator.copy_state(ctx.present_state, ctx.old_state, body, ctx)
            else:
                self.state_translator.copy_state(ctx.old_state, ctx.pre_old_state, body, ctx)

            def return_bool(value: bool) -> Stmt:
                lit = self.viper_ast.TrueLit if value else self.viper_ast.FalseLit
                return self.viper_ast.LocalVarAssign(success_var, lit())

            # If we do not encounter an exception we will return success
            body.append(return_bool(True))

            # Add variable for success(if_not=overflow) that tracks whether an overflow happened
            overflow_var = helpers.overflow_var(self.viper_ast)
            ctx.new_local_vars.append(overflow_var)
            overflow_var_assign = self.viper_ast.LocalVarAssign(overflow_var.localVar(), self.viper_ast.FalseLit())
            body.append(overflow_var_assign)

            # Add variable for whether we need to set old_self to current self
            # In the beginning, it is True as the first public state needs to
            # be checked against itself
            if is_init:
                ctx.new_local_vars.append(helpers.first_public_state_var(self.viper_ast))
                fps = helpers.first_public_state_var(self.viper_ast, pos).localVar()
                var_assign = self.viper_ast.LocalVarAssign(fps, self.viper_ast.TrueLit())
                body.append(var_assign)

            # Translate the performs clauses
            performs_clause_conditions = []
            interface_files = [ctx.program.interfaces[impl.name].file for impl in ctx.program.implements]
            for performs in function.performs:
                assert isinstance(performs, ast.FunctionCall)
                with ctx.state_scope(ctx.pre_state, ctx.pre_state):
                    address, resource = self.allocation_translator.location_address_of_performs(performs, body, ctx,
                                                                                                return_resource=True)
                if (resource is not None and resource.file is not None
                        and resource.file != ctx.program.file and resource.file in interface_files):
                    # All performs clauses with own resources of an implemented interface should be on that interface
                    apos = self.to_position(performs, ctx, rules.INTERFACE_RESOURCE_PERFORMS,
                                            values={'resource': resource})
                    cond = self.viper_ast.NeCmp(address, self_address, apos)
                    performs_clause_conditions.append(self.viper_ast.Assert(cond, apos))
                _ = self.specification_translator.translate_ghost_statement(performs, body, ctx, is_performs=True)

            for interface_type in ctx.program.implements:
                interface = ctx.program.interfaces[interface_type.name]
                interface_func = interface.functions.get(function.name)
                if interface_func:
                    with ctx.program_scope(interface):
                        for performs in interface_func.performs:
                            assert isinstance(performs, ast.FunctionCall)
                            self.specification_translator.translate_ghost_statement(performs, body, ctx,
                                                                                    is_performs=True)

            # Revert if a @nonreentrant lock is set
            self._assert_unlocked(function, body, ctx)
            # Set all @nonreentrant locks
            self._set_locked(function, True, body, ctx)

            # In the initializer initialize all fields to their default values
            if is_init:
                self.state_translator.initialize_state(ctx.current_state, body, ctx)
                # Havoc self.balance, because we are not allowed to assume self.balance == 0
                # in the beginning
                self._havoc_balance(body, ctx)
                if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
                    self.state_translator.copy_state(ctx.current_state, ctx.current_old_state, body, ctx,
                                                     unless=lambda n: (n != mangled.ALLOCATED
                                                                       and n != mangled.TRUSTED
                                                                       and n != mangled.OFFERED))
                    self.state_translator.havoc_state(ctx.current_state, body, ctx,
                                                      unless=lambda n: (n != mangled.ALLOCATED
                                                                        and n != mangled.TRUSTED
                                                                        and n != mangled.OFFERED))
                    self.expression_translator.assume_own_resources_stayed_constant(body, ctx, pos)
                    for _, interface in ctx.program.interfaces.items():
                        with ctx.quantified_var_scope():
                            var_name = mangled.quantifier_var_name(names.INTERFACE)
                            qvar = TranslatedVar(var_name, var_name, types.VYPER_ADDRESS, self.viper_ast)
                            ctx.quantified_vars[var_name] = qvar
                            self.expression_translator.implicit_resource_caller_private_expressions(
                                interface, qvar.local_var(ctx), self_address, body, ctx)

            # For public function we can make further assumptions about msg.value
            if function.is_public():
                msg_value = helpers.msg_value(self.viper_ast, ctx)
                if not function.is_payable():
                    # If the function is not payable we assume that msg.value == 0
                    # Technically speaking it is possible to send ether to a non-payable function
                    # which leads to a revert, however, we implicitly require all function calls
                    # to adhere to the Vyper function call interface (i.e., that they have the
                    # correct types and ether).
                    zero = self.viper_ast.IntLit(0)
                    is_zero = self.viper_ast.EqCmp(msg_value, zero)
                    payable_info = self.to_info(["Function is not payable"])
                    assume = self.viper_ast.Inhale(is_zero, info=payable_info)
                    body.append(assume)
                else:
                    # Increase balance by msg.value
                    payable_info = self.to_info(["Function is payable"])
                    self.balance_translator.increase_balance(msg_value, body, ctx, info=payable_info)

                    # Increase received for msg.sender by msg.value
                    self.balance_translator.increase_received(msg_value, body, ctx)

                    # Allocate the received ether to the sender
                    if (ctx.program.config.has_option(names.CONFIG_ALLOCATION)
                            and not ctx.program.config.has_option(names.CONFIG_NO_DERIVED_WEI)):
                        resource = self.resource_translator.translate(None, body, ctx)  # Wei resource
                        self.allocation_translator.allocate_derived(
                            function.node, resource, msg_sender, msg_sender, msg_value, body, ctx, pos)

            # If we are in a synthesized init, we don't have a function body
            if function.node:
                body_stmts = []
                self.statement_translator.translate_stmts(function.node.body, body_stmts, ctx)
                self.seqn_with_info(body_stmts, "Function body", body)

            # If we reach this point we either jumped to it by returning or got there directly
            # because we didn't revert (yet)
            body.append(return_label)

            # Check that we were allowed to inhale the performs clauses
            body.extend(performs_clause_conditions)

            # Unset @nonreentrant locks
            self._set_locked(function, False, body, ctx)

            # Add variable for success(if_not=out_of_gas) that tracks whether the contract ran out of gas
            out_of_gas_var = helpers.out_of_gas_var(self.viper_ast)
            ctx.new_local_vars.append(out_of_gas_var)
            # Fail, if we ran out of gas
            # If the no_gas option is set, ignore it
            if not ctx.program.config.has_option(names.CONFIG_NO_GAS):
                self.fail_if(out_of_gas_var.localVar(), [], body, ctx)

            # If we reach this point do not revert the state
            body.append(self.viper_ast.Goto(mangled.END_LABEL))
            # Revert the state label
            body.append(revert_label)
            # Return False
            body.append(return_bool(False))
            # Havoc the return value
            if function.type.return_type:
                result_type = self.type_translator.translate(ctx.result_var.type, ctx)
                havoc = helpers.havoc_var(self.viper_ast, result_type, ctx)
                body.append(self.viper_ast.LocalVarAssign(ctx.result_var.local_var(ctx), havoc))
            # Revert self and old_self to the state before the function
            self.state_translator.copy_state(ctx.pre_state, ctx.present_state, body, ctx)
            if function.is_private():
                # In private functions the pre_state is not equal the old_state. For this we have the pre_old_state.
                # This is the case since for private function the pre_state may not be a public state.
                self.state_translator.copy_state(ctx.pre_old_state, ctx.old_state, body, ctx)
            else:
                self.state_translator.copy_state(ctx.pre_state, ctx.old_state, body, ctx)

            # The end of a program, label where return statements jump to
            body.append(end_label)

            # Postconditions hold for single transactions, checks hold before any public state,
            # invariants across transactions.
            # Therefore, after the function execution the following steps happen:
            #   - Assert the specified postconditions of the function
            #   - If the function is public
            #       - Assert the checks
            #       - Havoc self.balance
            #       - Assert invariants
            #       - Check accessible
            # This is necessary because a contract may receive additional money through
            # selfdestruct or mining

            # In init set old to current self, if this is the first public state
            # However, the state has to be set again after havocing the balance, therefore
            # we don't update the flag
            if is_init:
                self.state_translator.check_first_public_state(body, ctx, False)
                self.expression_translator.assume_contract_state(known_interface_ref, body, ctx,
                                                                 skip_caller_private=True)

            post_stmts = []

            old_state = ctx.present_state if is_init else ctx.pre_state
            with ctx.state_scope(ctx.present_state, old_state):
                # Save model vars
                model_translator = self.model_translator.save_variables(post_stmts, ctx)
                # Assert postconditions
                for post in function.postconditions:
                    post_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL, modelt=model_translator)
                    cond = self.specification_translator.translate_pre_or_postcondition(post, post_stmts, ctx)
                    post_assert = self.viper_ast.Exhale(cond, post_pos)
                    post_stmts.append(post_assert)

                for post in chain(ctx.program.general_postconditions, ctx.program.transitive_postconditions):
                    post_pos = self.to_position(post, ctx)
                    cond = self.specification_translator.translate_pre_or_postcondition(post, post_stmts, ctx)
                    if is_init:
                        init_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL, modelt=model_translator)
                        # General postconditions only have to hold for init if it succeeds
                        cond = self.viper_ast.Implies(success_var, cond, post_pos)
                        post_stmts.append(self.viper_ast.Assert(cond, init_pos))
                    else:
                        via = [Via('general postcondition', post_pos)]
                        func_pos = self.to_position(function.node, ctx, rules.POSTCONDITION_FAIL, via, model_translator)
                        post_stmts.append(self.viper_ast.Assert(cond, func_pos))

                # The postconditions of the interface the contract is supposed to implement
                for interface_type in ctx.program.implements:
                    interface = ctx.program.interfaces[interface_type.name]
                    interface_func = interface.functions.get(function.name)
                    if interface_func:
                        postconditions = chain(interface_func.postconditions, interface.general_postconditions)
                    else:
                        postconditions = interface.general_postconditions

                    for post in postconditions:
                        post_pos = self.to_position(function.node or post, ctx)
                        with ctx.program_scope(interface):
                            cond = self.specification_translator.translate_pre_or_postcondition(post, post_stmts, ctx)
                            if is_init:
                                cond = self.viper_ast.Implies(success_var, cond, post_pos)
                        apos = self.to_position(function.node or post, ctx,
                                                rules.INTERFACE_POSTCONDITION_FAIL, modelt=model_translator)
                        post_assert = self.viper_ast.Assert(cond, apos)
                        post_stmts.append(post_assert)

            self.seqn_with_info(post_stmts, "Assert postconditions", body)

            # Checks and Invariants can be checked in the end of public functions
            # but not in the end of private functions
            if function.is_public():
                # Assert checks
                # For the checks we need to differentiate between success and failure because we
                # on failure the assertion is evaluated in the old heap where events where not
                # inhaled yet
                checks_succ = []
                checks_fail = []
                for check in function.checks:
                    check_pos = self.to_position(check, ctx, rules.CHECK_FAIL, modelt=model_translator)
                    cond_succ = self.specification_translator.translate_check(check, checks_succ, ctx, False)
                    checks_succ.append(self.viper_ast.Assert(cond_succ, check_pos))
                    # Checks do not have to hold if init fails
                    if not is_init:
                        cond_fail = self.specification_translator.translate_check(check, checks_fail, ctx, True)
                        checks_fail.append(self.viper_ast.Assert(cond_fail, check_pos))

                self.expression_translator.assert_caller_private(model_translator, checks_succ, ctx,
                                                                 [Via('end of function body', pos)])
                for check in ctx.program.general_checks:
                    cond_succ = self.specification_translator.translate_check(check, checks_succ, ctx, False)

                    # If we are in the initializer we might have a synthesized __init__, therefore
                    # just use always check as position, else use function as position and create
                    # via to always check
                    if is_init:
                        check_pos = self.to_position(check, ctx, rules.CHECK_FAIL, modelt=model_translator)
                    else:
                        check_pos = self.to_position(check, ctx)
                        via = [Via('check', check_pos)]
                        check_pos = self.to_position(function.node, ctx, rules.CHECK_FAIL, via, model_translator)

                    checks_succ.append(self.viper_ast.Assert(cond_succ, check_pos))
                    # Checks do not have to hold if __init__ fails
                    if not is_init:
                        cond_fail = self.specification_translator.translate_check(check, checks_fail, ctx, True)
                        checks_fail.append(self.viper_ast.Assert(cond_fail, check_pos))

                body.extend(helpers.flattened_conditional(self.viper_ast, success_var, checks_succ, checks_fail))
                # Havoc self.balance
                self._havoc_balance(body, ctx)

                # In init set old to current self, if this is the first public state
                if is_init:
                    self.state_translator.check_first_public_state(body, ctx, False)

                # Havoc other contract state
                self.state_translator.havoc_state_except_self(ctx.current_state, body, ctx)

                def assert_collected_invariants(collected_invariants) -> List[Expr]:
                    invariant_assertions = []
                    # Assert collected invariants
                    for invariant, invariant_condition in collected_invariants:
                        invariant_pos = self.to_position(invariant, ctx)
                        # If we have a synthesized __init__ we only create an
                        # error message on the invariant
                        if is_init:
                            # Invariants do not have to hold if __init__ fails
                            invariant_condition = self.viper_ast.Implies(success_var, invariant_condition,
                                                                         invariant_pos)
                            assertion_pos = self.to_position(invariant, ctx, rules.INVARIANT_FAIL,
                                                             modelt=invariant_model_translator)
                        else:
                            assertion_pos = self.to_position(function.node, ctx, rules.INVARIANT_FAIL,
                                                             [Via('invariant', invariant_pos)],
                                                             invariant_model_translator)

                        invariant_assertions.append(self.viper_ast.Assert(invariant_condition, assertion_pos))
                    return invariant_assertions

                # Assert the invariants
                invariant_stmts = []
                invariant_model_translator = self.model_translator.save_variables(invariant_stmts, ctx, pos)

                # Collect all local state invariants
                invariant_conditions = []
                for interface_type in ctx.program.implements:
                    interface = ctx.program.interfaces[interface_type.name]
                    with ctx.program_scope(interface):
                        for inv in ctx.current_program.local_state_invariants:
                            cond = self.specification_translator.translate_invariant(inv, invariant_stmts, ctx, True)
                            invariant_conditions.append((inv, cond))
                for inv in ctx.current_program.local_state_invariants:
                    # We ignore accessible here because we use a separate check
                    cond = self.specification_translator.translate_invariant(inv, invariant_stmts, ctx, True)
                    invariant_conditions.append((inv, cond))

                invariant_stmts.extend(assert_collected_invariants(invariant_conditions))
                self.seqn_with_info(invariant_stmts, "Assert Local State Invariants", body)

                self.expression_translator.assume_contract_state(known_interface_ref, body, ctx)

                # Collect all inter contract invariants
                invariant_stmts = []
                invariant_conditions = []
                for interface_type in ctx.program.implements:
                    interface = ctx.program.interfaces[interface_type.name]
                    with ctx.program_scope(interface):
                        for inv in ctx.current_program.inter_contract_invariants:
                            cond = self.specification_translator.translate_invariant(inv, invariant_stmts, ctx, True)
                            invariant_conditions.append((inv, cond))
                for inv in ctx.current_program.inter_contract_invariants:
                    # We ignore accessible here because we use a separate check
                    cond = self.specification_translator.translate_invariant(inv, invariant_stmts, ctx, True)
                    invariant_conditions.append((inv, cond))

                invariant_stmts.extend(assert_collected_invariants(invariant_conditions))
                self.seqn_with_info(invariant_stmts, "Assert Inter Contract Invariants", body)

                if is_init:
                    derived_resources_invariants = [
                        self.viper_ast.Assert(self.viper_ast.Implies(success_var, expr, expr.pos()), expr.pos())
                        for expr in ctx.derived_resources_invariants(function.node)]
                else:
                    derived_resources_invariants = [
                        self.viper_ast.Assert(expr, expr.pos())
                        for expr in ctx.derived_resources_invariants(function.node)]
                self.seqn_with_info(derived_resources_invariants, "Assert derived resource invariants", body)

                # We check that the invariant tracks all allocation by doing a leak check.
                # We also check that all necessary operations stated in perform clauses were
                # performed.
                if ctx.program.config.has_option(names.CONFIG_ALLOCATION):
                    self.allocation_translator.function_leak_check(body, ctx, pos)

                # We check accessibility by inhaling a predicate in the corresponding function
                # and checking in the end that if it has been inhaled (i.e. if we want to prove
                # that some amount is a accessible) the amount has been sent to msg.sender
                # forall a: wei_value :: perm(accessible(tag, msg.sender, a, <args>)) > 0 ==>
                #   success(if_not=out_of_gas or sender_failed) and
                #   success() ==> sent(msg.sender) - old(sent(msg.sender)) >= a
                # The tag is used to differentiate between the different invariants the accessible
                # expressions occur in
                accessibles = []
                for tag in function.analysis.accessible_tags:
                    # It shouldn't be possible to write accessible for __init__
                    assert function.node

                    tag_inv = ctx.program.analysis.inv_tags[tag]
                    inv_pos = self.to_position(tag_inv, ctx)
                    vias = [Via('invariant', inv_pos)]
                    acc_pos = self.to_position(function.node, ctx, rules.INVARIANT_FAIL,
                                               vias, invariant_model_translator)

                    wei_value_type = self.type_translator.translate(types.VYPER_WEI_VALUE, ctx)
                    amount_var = self.viper_ast.LocalVarDecl('$a', wei_value_type, inv_pos)
                    acc_name = mangled.accessible_name(function.name)
                    tag_lit = self.viper_ast.IntLit(tag, inv_pos)
                    msg_sender = helpers.msg_sender(self.viper_ast, ctx, inv_pos)
                    amount_local = self.viper_ast.LocalVar('$a', wei_value_type, inv_pos)

                    arg_vars = [arg.local_var(ctx, inv_pos) for arg in args.values()]
                    acc_args = [tag_lit, msg_sender, amount_local, *arg_vars]
                    acc_pred = self.viper_ast.PredicateAccess(acc_args, acc_name, inv_pos)
                    acc_perm = self.viper_ast.CurrentPerm(acc_pred, inv_pos)
                    pos_perm = self.viper_ast.GtCmp(acc_perm, self.viper_ast.NoPerm(inv_pos), inv_pos)

                    sender_failed = helpers.check_call_failed(self.viper_ast, msg_sender, inv_pos)
                    out_of_gas = helpers.out_of_gas_var(self.viper_ast, inv_pos).localVar()
                    not_sender_failed = self.viper_ast.Not(self.viper_ast.Or(sender_failed, out_of_gas, inv_pos),
                                                           inv_pos)
                    succ_if_not = self.viper_ast.Implies(not_sender_failed,
                                                         ctx.success_var.local_var(ctx, inv_pos), inv_pos)

                    sent_to = self.balance_translator.get_sent(self_var, msg_sender, ctx, inv_pos)
                    pre_sent_to = self.balance_translator.get_sent(pre_self_var, msg_sender, ctx, inv_pos)

                    diff = self.viper_ast.Sub(sent_to, pre_sent_to, inv_pos)
                    ge_sent_local = self.viper_ast.GeCmp(diff, amount_local, inv_pos)
                    succ_impl = self.viper_ast.Implies(ctx.success_var.local_var(ctx, inv_pos), ge_sent_local, inv_pos)
                    conj = self.viper_ast.And(succ_if_not, succ_impl, inv_pos)
                    impl = self.viper_ast.Implies(pos_perm, conj, inv_pos)
                    trigger = self.viper_ast.Trigger([acc_pred], inv_pos)
                    forall = self.viper_ast.Forall([amount_var], [trigger], impl, inv_pos)
                    accessibles.append(self.viper_ast.Assert(forall, acc_pos))

                self.seqn_with_info(accessibles, "Assert accessibles", body)

            args_list = [arg.var_decl(ctx) for arg in args.values()]
            locals_list = [local.var_decl(ctx) for local in chain(local_vars.values(), state)]
            locals_list = [*locals_list, *ctx.new_local_vars]
            ret_list = [ret.var_decl(ctx) for ret in return_variables]

            viper_name = mangled.method_name(function.name)
            method = self.viper_ast.Method(viper_name, args_list, ret_list, [], [], locals_list, body, pos)

            if is_init and do_performs:
                ctx.program.config.options = [option for option in ctx.program.config.options
                                              if option != names.CONFIG_NO_PERFORMS]

            return method

    @staticmethod
    def can_assume_private_function(function: VyperFunction) -> bool:
        if function.postconditions or function.preconditions or function.checks:
            return True
        return False

    def inline(self, call: ast.ReceiverCall, args: List[Expr], res: List[Stmt], ctx: Context) -> Expr:
        function = ctx.program.functions[call.name]
        if function.is_pure():
            return self._call_pure(call, args, res, ctx)
        elif self.can_assume_private_function(function):
            return self._assume_private_function(call, args, res, ctx)
        else:
            return self._inline(call, args, res, ctx)

    def _inline(self, call: ast.ReceiverCall, args: List[Expr], res: List[Stmt], ctx: Context) -> Expr:
        function = ctx.program.functions[call.name]
        call_pos = self.to_position(call, ctx)
        via = Via('inline', call_pos)
        with ctx.inline_scope(via, function):
            assert function.node
            # Only private self-calls are allowed in Vyper
            assert function.is_private()

            pos = self.to_position(function.node, ctx)
            body = []

            # We keep the msg variable the same, as only msg.gas is allowed in the body of a private function.
            # In specifications we assume inline semantics, i.e., msg.sender and msg.value in the inlined function
            # correspond to msg.sender and msg.value in the caller function.

            self._generate_arguments_as_local_vars(function, args, body, pos, ctx)

            # Define return var
            if function.type.return_type:
                ret_name = ctx.inline_prefix + mangled.RESULT_VAR
                ctx.result_var = TranslatedVar(names.RESULT, ret_name, function.type.return_type, self.viper_ast, pos)
                ctx.new_local_vars.append(ctx.result_var.var_decl(ctx, pos))
                ret_var = ctx.result_var.local_var(ctx, pos)
            else:
                ret_var = None

            # Define return label for inlined return statements
            return_label_name = ctx.inline_prefix + mangled.RETURN_LABEL
            return_label = self.viper_ast.Label(return_label_name)
            ctx.return_label = return_label_name

            old_state_for_postconditions = ctx.current_state
            if not function.is_constant():
                # Create pre_state for private function
                def inlined_pre_state(name: str) -> str:
                    return ctx.inline_prefix + mangled.pre_state_var_name(name)

                old_state_for_postconditions = self.state_translator.state(inlined_pre_state, ctx)
                for val in old_state_for_postconditions.values():
                    ctx.new_local_vars.append(val.var_decl(ctx, pos))

                # Copy present state to this created pre_state
                self.state_translator.copy_state(ctx.current_state, old_state_for_postconditions, res, ctx)

            # Revert if a @nonreentrant lock is set
            self._assert_unlocked(function, body, ctx)
            # Set @nonreentrant locks
            self._set_locked(function, True, body, ctx)

            # Translate body
            self.statement_translator.translate_stmts(function.node.body, body, ctx)

            # Unset @nonreentrant locks
            self._set_locked(function, False, body, ctx)

            post_stmts = []
            with ctx.state_scope(ctx.current_state, old_state_for_postconditions):
                for post in chain(ctx.program.general_postconditions, ctx.program.transitive_postconditions):
                    cond = self.specification_translator.translate_pre_or_postcondition(post, post_stmts, ctx)
                    post_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL, values={'function': function})
                    post_stmts.append(self.viper_ast.Assert(cond, post_pos))

                for interface_type in ctx.program.implements:
                    interface = ctx.program.interfaces[interface_type.name]
                    postconditions = interface.general_postconditions
                    for post in postconditions:
                        with ctx.program_scope(interface):
                            cond = self.specification_translator.translate_pre_or_postcondition(post, post_stmts, ctx)
                        post_pos = self.to_position(post, ctx, rules.POSTCONDITION_FAIL, values={'function': function})
                        post_stmts.append(self.viper_ast.Inhale(cond, post_pos))
            self.seqn_with_info(post_stmts, f"Assert general postconditions", body)

            self.seqn_with_info(body, f"Inlined call of {function.name}", res)
            res.append(return_label)
            return ret_var

    def _call_pure(self, call: ast.ReceiverCall, args: List[Expr], res: List[Expr], ctx: Context) -> Expr:
        function = ctx.program.functions[call.name]
        function_args = args.copy()
        for (name, _), arg in zip_longest(function.args.items(), args):
            if not arg:
                function_args.append(self.expression_translator.translate(function.defaults[name], res, ctx))
        function = ctx.program.functions[call.name]
        return_type = self.viper_ast.Bool
        if function.type.return_type:
            return_type = self.type_translator.translate(function.type.return_type, ctx)
        mangled_name = mangled.pure_function_name(call.name)
        call_pos = self.to_position(call, ctx)
        via = Via('pure function call', call_pos)
        pos = self.to_position(function.node, ctx, vias=[via])
        func_app = self.viper_ast.FuncApp(mangled_name, [ctx.self_var.local_var(ctx), *function_args], pos,
                                          type=helpers.struct_type(self.viper_ast))
        called_success_var = helpers.struct_pure_get_success(self.viper_ast, func_app, pos)
        called_result_var = helpers.struct_pure_get_result(self.viper_ast, func_app, return_type, pos)
        self.fail_if(self.viper_ast.Not(called_success_var), [], res, ctx, pos)
        return called_result_var

    def _assume_private_function(self, call: ast.ReceiverCall, args: List[Expr], res: List[Stmt], ctx: Context) -> Expr:
        # Assume private functions are translated as follows:
        #    - Evaluate arguments
        #    - Define return variable
        #    - Define new_success variable
        #    - Check precondition
        #    - Forget about all events
        #    - The next steps are only necessary if the function is not constant:
        #       - Create new state which corresponds to the pre_state of the private function call
        #       - Havoc self and contracts
        #       - Havoc old_self and old_contracts
        #       - Assume type assumptions for self and old_self
        #       - Assume invariants (where old and present refers to the havoced old state)
        #    - Check that private function has stronger "check"s
        #    - Assume postconditions (where old refers to present state, if the function is constant or
        #      else to the newly create pre_state)
        #    - Fail if not new_success
        #    - Wrap integers to $Int if the function has a numeric return type
        function = ctx.program.functions[call.name]
        call_pos = self.to_position(call, ctx)
        via = Via('private function call', call_pos)
        with ctx.inline_scope(via):
            assert function.node
            # Only private self-calls are allowed in Vyper
            assert function.is_private()

            pos = self.to_position(function.node, ctx)

            args_as_local_vars = []
            self._generate_arguments_as_local_vars(function, args, args_as_local_vars, pos, ctx)
            self.seqn_with_info(args_as_local_vars, "Arguments of private function call", res)

            # Define success var
            succ_name = ctx.inline_prefix + mangled.SUCCESS_VAR
            ctx.success_var = TranslatedVar(names.SUCCESS, succ_name, types.VYPER_BOOL, self.viper_ast, pos)
            ctx.new_local_vars.append(ctx.success_var.var_decl(ctx, pos))
            success_var = ctx.success_var.local_var(ctx, pos)

            # Define return var
            if function.type.return_type:
                ret_name = ctx.inline_prefix + mangled.RESULT_VAR
                ctx.result_var = TranslatedVar(names.RESULT, ret_name, function.type.return_type, self.viper_ast, pos)
                ctx.new_local_vars.append(ctx.result_var.var_decl(ctx, pos))
                ret_var = ctx.result_var.local_var(ctx, pos)
            else:
                ret_var = None

            # Check preconditions
            pre_stmts = []
            with ctx.state_scope(ctx.current_state, ctx.current_old_state):
                for precondition in function.preconditions:
                    cond = self.specification_translator.translate_pre_or_postcondition(precondition, pre_stmts, ctx)
                    pre_pos = self.to_position(precondition, ctx, rules.PRECONDITION_FAIL,
                                               values={'function': function})
                    pre_stmts.append(self.viper_ast.Exhale(cond, pre_pos))

            self.seqn_with_info(pre_stmts, "Check preconditions", res)

            # We forget about events by exhaling all permissions to the event predicates
            # and then inhale an unspecified permission amount.
            event_handling = []
            self.expression_translator.forget_about_all_events(event_handling, ctx, pos)
            self.expression_translator.log_all_events_zero_or_more_times(event_handling, ctx, pos)
            self.seqn_with_info(event_handling, "Assume we know nothing about events", res)

            old_state_for_postconditions = ctx.current_state
            if not function.is_constant():
                # Create pre_state for private function
                def inlined_pre_state(name: str) -> str:
                    return ctx.inline_prefix + mangled.pre_state_var_name(name)
                old_state_for_postconditions = self.state_translator.state(inlined_pre_state, ctx)
                for val in old_state_for_postconditions.values():
                    ctx.new_local_vars.append(val.var_decl(ctx, pos))

                # Copy present state to this created pre_state
                self.state_translator.copy_state(ctx.current_state, old_state_for_postconditions, res, ctx)

                self.state_translator.havoc_old_and_current_state(self.specification_translator, res, ctx, pos)

            private_function_checks_conjunction = self.viper_ast.TrueLit(pos)
            for check in function.checks:
                cond = self.specification_translator.translate_check(check, res, ctx)
                private_function_checks_conjunction = self.viper_ast.And(private_function_checks_conjunction, cond, pos)

            check_stmts = []
            for check in ctx.function.checks:
                check_cond = self.specification_translator.translate_check(check, res, ctx)
                check_pos = self.to_position(check, ctx, rules.PRIVATE_CALL_CHECK_FAIL)
                cond = self.viper_ast.Implies(private_function_checks_conjunction, check_cond, check_pos)
                check_stmts.append(self.viper_ast.Assert(cond, check_pos))

            self.seqn_with_info(check_stmts, "Check strength of checks of private function", res)

            post_stmts = []
            with ctx.state_scope(ctx.current_state, old_state_for_postconditions):
                # Assume postconditions
                for post in function.postconditions:
                    cond = self.specification_translator.\
                        translate_pre_or_postcondition(post, post_stmts, ctx, assume_events=True)
                    post_pos = self.to_position(post, ctx, rules.INHALE_POSTCONDITION_FAIL)
                    post_stmts.append(self.viper_ast.Inhale(cond, post_pos))

                for post in chain(ctx.program.general_postconditions, ctx.program.transitive_postconditions):
                    cond = self.specification_translator.translate_pre_or_postcondition(post, post_stmts, ctx)
                    post_pos = self.to_position(post, ctx, rules.INHALE_POSTCONDITION_FAIL)
                    post_stmts.append(self.viper_ast.Inhale(cond, post_pos))

                for interface_type in ctx.program.implements:
                    interface = ctx.program.interfaces[interface_type.name]
                    postconditions = interface.general_postconditions
                    for post in postconditions:
                        with ctx.program_scope(interface):
                            cond = self.specification_translator.translate_pre_or_postcondition(post, post_stmts, ctx)
                        post_pos = self.to_position(post, ctx, rules.INHALE_POSTCONDITION_FAIL)
                        post_stmts.append(self.viper_ast.Inhale(cond, post_pos))

            self.seqn_with_info(post_stmts, "Assume postconditions", res)

            self.fail_if(self.viper_ast.Not(success_var), [], res, ctx, call_pos)

            if (types.is_numeric(function.type.return_type)
                    and self.expression_translator.arithmetic_translator.is_unwrapped(ret_var)):
                ret_var = helpers.w_wrap(self.viper_ast, ret_var)
            return ret_var

    def _generate_arguments_as_local_vars(self, function, args, res, pos, ctx):
        # Add arguments to local vars, assign passed args or default argument
        for (name, var), arg in zip_longest(function.args.items(), args):
            apos = self.to_position(var.node, ctx)
            translated_arg = self._translate_var(var, ctx, True)
            ctx.args[name] = translated_arg
            if not arg:
                arg = self.expression_translator.translate(function.defaults[name], res, ctx)
            lhs = translated_arg.local_var(ctx)
            if (types.is_numeric(translated_arg.type)
                    and self.expression_translator.arithmetic_translator.is_wrapped(arg)
                    and self.expression_translator.arithmetic_translator.is_unwrapped(lhs)):
                translated_arg.is_local = False
                lhs = translated_arg.local_var(ctx)
            elif (types.is_numeric(translated_arg.type)
                    and self.expression_translator.arithmetic_translator.is_unwrapped(arg)
                    and self.expression_translator.arithmetic_translator.is_wrapped(lhs)):
                arg = helpers.w_wrap(self.viper_ast, arg)
            elif (not types.is_numeric(translated_arg.type)
                    and self.expression_translator.arithmetic_translator.is_wrapped(arg)):
                arg = helpers.w_unwrap(self.viper_ast, arg)
            ctx.new_local_vars.append(translated_arg.var_decl(ctx, pos))
            res.append(self.viper_ast.LocalVarAssign(lhs, arg, apos))

    def _translate_var(self, var: VyperVar, ctx: Context, is_local: bool):
        pos = self.to_position(var.node, ctx)
        name = mangled.local_var_name(ctx.inline_prefix, var.name)
        return TranslatedVar(var.name, name, var.type, self.viper_ast, pos, is_local=is_local)

    def _assume_non_negative(self, var, res: List[Stmt]):
        zero = self.viper_ast.IntLit(0)
        gez = self.viper_ast.GeCmp(var, zero)
        res.append(self.viper_ast.Inhale(gez))

    def _havoc_balance(self, res: List[Stmt], ctx: Context):
        balance_type = ctx.field_types[names.ADDRESS_BALANCE]
        havoc = helpers.havoc_var(self.viper_ast, balance_type, ctx)
        self._assume_non_negative(havoc, res)
        self.balance_translator.increase_balance(havoc, res, ctx)

    def _assert_unlocked(self, function: VyperFunction, res: List[Stmt], ctx: Context):
        keys = function.nonreentrant_keys()
        locked = [helpers.get_lock(self.viper_ast, key, ctx) for key in keys]
        if locked:
            cond = reduce(self.viper_ast.Or, locked)
            self.fail_if(cond, [], res, ctx)

    def _set_locked(self, function: VyperFunction, value: bool, res: List[Stmt], ctx: Context):
        keys = function.nonreentrant_keys()
        self_var = ctx.self_var.local_var(ctx)

        def set_lock(key):
            return helpers.set_lock(self.viper_ast, key, value, ctx)

        res.extend(self.viper_ast.LocalVarAssign(self_var, set_lock(key)) for key in keys)
