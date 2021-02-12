"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Optional

from twovyper.ast import ast_nodes as ast, types
from twovyper.ast.types import StructType, VYPER_BOOL, VYPER_UINT256

from twovyper.exceptions import UnsupportedException

from twovyper.translation import helpers, LocalVarSnapshot
from twovyper.translation.context import Context
from twovyper.translation.pure_translators import PureTranslatorMixin, PureExpressionTranslator, \
    PureArithmeticTranslator, PureSpecificationTranslator, PureTypeTranslator
from twovyper.translation.statement import AssignmentTranslator, StatementTranslator
from twovyper.translation.variable import TranslatedPureIndexedVar

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr


class PureStatementTranslator(PureTranslatorMixin, StatementTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.expression_translator = PureExpressionTranslator(viper_ast)
        self.assignment_translator = _AssignmentTranslator(viper_ast)
        self.arithmetic_translator = PureArithmeticTranslator(viper_ast)
        self.specification_translator = PureSpecificationTranslator(viper_ast)
        self.type_translator = PureTypeTranslator(viper_ast)
        self.viper_struct_type = helpers.struct_type(self.viper_ast)
        self.function_result = self.viper_ast.Result(self.viper_struct_type)

    def visit(self, node, *args):
        if not node.is_ghost_code:
            super().visit(node, *args)

    def translate_stmts(self, stmts: List[ast.Stmt], res: List[Expr], ctx: Context):
        for s in stmts:
            self.translate(s, res, ctx)

    def translate_AnnAssign(self, node: ast.AnnAssign, res: List[Expr], ctx: Context):
        pos = self.to_position(node, ctx)

        self._add_local_var(node.target, ctx)
        lhs = ctx.all_vars[node.target.id]

        if node.value is None:
            vyper_type = node.target.type
            rhs = self.type_translator.default_value(None, vyper_type, res, ctx)
        elif types.is_numeric(node.value.type):
            rhs = self.expression_translator.translate_top_level_expression(node.value, res, ctx)
        else:
            # Ignore the $wrap information, if the node is not numeric
            rhs = self.expression_translator.translate(node.value, res, ctx)

        if self.arithmetic_translator.is_wrapped(rhs):
            if types.is_numeric(node.value.type):
                lhs.new_idx()
                lhs.is_local = False
            else:
                rhs = helpers.w_unwrap(self.viper_ast, rhs)
        assign = self.viper_ast.EqCmp(lhs.local_var(ctx, pos), rhs, pos)
        expr = self.viper_ast.Implies(ctx.pure_conds, assign, pos) if ctx.pure_conds else assign
        res.append(expr)

    def translate_Log(self, node: ast.Log, res: List[Expr], ctx: Context):
        assert False

    def translate_Raise(self, node: ast.Raise, res: List[Expr], ctx: Context):
        pos = self.to_position(node, ctx)
        self.fail_if(self.viper_ast.TrueLit(pos), [], res, ctx, pos)
        ctx.pure_conds = self.viper_ast.FalseLit(pos)

    def translate_Assert(self, node: ast.Assert, res: List[Expr], ctx: Context):
        pos = self.to_position(node, ctx)
        expr = self.expression_translator.translate(node.test, res, ctx)
        cond = self.viper_ast.Not(expr, pos)
        self.fail_if(cond, [], res, ctx, pos)

    def translate_Return(self, node: ast.Return, res: List[Expr], ctx: Context):
        assert node.value
        assert isinstance(ctx.result_var, TranslatedPureIndexedVar)
        assert isinstance(ctx.success_var, TranslatedPureIndexedVar)
        pos = self.to_position(node, ctx)

        expr = self.expression_translator.translate_top_level_expression(node.value, res, ctx)
        if (self.arithmetic_translator.is_unwrapped(ctx.result_var.local_var(ctx))
                and self.arithmetic_translator.is_wrapped(expr)):
            expr = helpers.w_unwrap(self.viper_ast, expr)

        ctx.result_var.new_idx()
        assign = self.viper_ast.EqCmp(ctx.result_var.local_var(ctx), expr, pos)
        expr = self.viper_ast.Implies(ctx.pure_conds, assign, pos) if ctx.pure_conds else assign
        res.append(expr)
        cond = ctx.pure_conds or self.viper_ast.TrueLit(pos)
        ctx.pure_returns.append((cond, ctx.result_var.evaluate_idx(ctx)))
        ctx.pure_success.append((cond, ctx.success_var.evaluate_idx(ctx)))

    def translate_If(self, node: ast.If, res: List[Expr], ctx: Context):
        pre_locals = self._local_variable_snapshot(ctx)
        pre_conds = ctx.pure_conds

        pos = self.to_position(node, ctx)
        cond = self.expression_translator.translate(node.test, res, ctx)

        cond_var = TranslatedPureIndexedVar('cond', 'cond', VYPER_BOOL, self.viper_ast, pos)
        assign = self.viper_ast.EqCmp(cond_var.local_var(ctx), cond, pos)
        expr = self.viper_ast.Implies(ctx.pure_conds, assign, pos) if ctx.pure_conds else assign
        res.append(expr)
        cond_local_var = cond_var.local_var(ctx)

        # "Then" branch
        with ctx.new_local_scope():
            # Update condition
            ctx.pure_conds = self.viper_ast.And(pre_conds, cond_local_var, pos) if pre_conds else cond_local_var
            with self.assignment_translator.assume_everything_has_wrapped_information():
                self.translate_stmts(node.body, res, ctx)
            # Get current state of local variable state after "then"-branch
            then_locals = self._local_variable_snapshot(ctx)
        # Reset indices of local variables in context
        self._reset_variable_to_snapshot(pre_locals, ctx)
        # "Else" branch
        with ctx.new_local_scope():
            # Update condition
            negated_local_var = self.viper_ast.Not(cond_local_var, pos)
            ctx.pure_conds = self.viper_ast.And(pre_conds, negated_local_var, pos) if pre_conds else negated_local_var
            with self.assignment_translator.assume_everything_has_wrapped_information():
                self.translate_stmts(node.orelse, res, ctx)
            # Get current state of local variable state after "else"-branch
            else_locals = self._local_variable_snapshot(ctx)
        # Update condition
        ctx.pure_conds = pre_conds
        # Merge variable changed in the "then" or "else" branch
        self._merge_snapshots(cond_local_var, then_locals, else_locals, res, ctx)

    def translate_For(self, node: ast.For, res: List[Expr], ctx: Context):
        pos = self.to_position(node, ctx)

        pre_conds = ctx.pure_conds

        self._add_local_var(node.target, ctx)
        loop_var_name = node.target.id
        loop_var = ctx.locals[loop_var_name]
        assert isinstance(loop_var, TranslatedPureIndexedVar)
        array = self.expression_translator.translate_top_level_expression(node.iter, res, ctx)
        loop_var.is_local = False
        array_var = TranslatedPureIndexedVar('array', 'array', node.iter.type, self.viper_ast, pos, is_local=False)
        res.append(self.viper_ast.EqCmp(array_var.local_var(ctx), array, pos))
        array_local_var = array_var.local_var(ctx)

        times = node.iter.type.size
        lpos = self.to_position(node.target, ctx)
        rpos = self.to_position(node.iter, ctx)

        if times > 0:
            has_numeric_array = types.is_numeric(node.target.type)
            loop_invariants = ctx.function.loop_invariants.get(node)
            if loop_invariants:
                # loop-array expression
                ctx.loop_arrays[loop_var_name] = array_local_var
                # New variable loop-idx
                loop_idx_var = TranslatedPureIndexedVar('idx', 'idx', VYPER_UINT256, self.viper_ast, pos)
                ctx.loop_indices[loop_var_name] = loop_idx_var
                loop_idx_local_var = loop_idx_var.local_var(ctx)
                # Havoc used variables
                loop_used_var = {}
                for var_name in ctx.function.analysis.loop_used_names.get(loop_var_name, []):
                    if var_name == loop_var_name:
                        continue
                    var = ctx.locals.get(var_name)
                    if var and isinstance(var, TranslatedPureIndexedVar):
                        # Create new variable
                        mangled_name = ctx.new_local_var_name(var.name)
                        new_var = TranslatedPureIndexedVar(var.name, mangled_name, var.type,
                                                           var.viper_ast, var.pos, var.info, var.is_local)
                        copy_expr = self.viper_ast.EqCmp(new_var.local_var(ctx), var.local_var(ctx), rpos)
                        res.append(copy_expr)
                        loop_used_var[var.name] = new_var
                        # Havoc old var
                        var.new_idx()
                        var.is_local = False
                # Assume loop 0 <= index < |array|
                loop_idx_ge_zero = self.viper_ast.GeCmp(loop_idx_local_var, self.viper_ast.IntLit(0), rpos)
                times_lit = self.viper_ast.IntLit(times)
                loop_idx_lt_array_size = self.viper_ast.LtCmp(loop_idx_local_var, times_lit, rpos)
                loop_idx_assumption = self.viper_ast.And(loop_idx_ge_zero, loop_idx_lt_array_size, rpos)
                res.append(loop_idx_assumption)
                # Set loop variable to array[index]
                array_at = self.viper_ast.SeqIndex(array_local_var, loop_idx_local_var, rpos)
                if has_numeric_array:
                    array_at = helpers.w_wrap(self.viper_ast, array_at)
                set_loop_var = self.viper_ast.EqCmp(loop_var.local_var(ctx), array_at, lpos)
                res.append(set_loop_var)
                with ctx.old_local_variables_scope(loop_used_var):
                    with ctx.state_scope(ctx.current_state, ctx.current_state):
                        for loop_invariant in loop_invariants:
                            cond_pos = self.to_position(loop_invariant, ctx)
                            inv = self.specification_translator.translate_pre_or_postcondition(loop_invariant, res, ctx)
                            inv_var = TranslatedPureIndexedVar('inv', 'inv', VYPER_BOOL, self.viper_ast, cond_pos)
                            inv_local_var = inv_var.local_var(ctx)
                            assign = self.viper_ast.EqCmp(inv_local_var, inv, cond_pos)
                            expr = self.viper_ast.Implies(pre_conds, assign, cond_pos) if pre_conds else assign
                            res.append(expr)
                            ctx.pure_conds = self.viper_ast.And(ctx.pure_conds, inv_local_var, pos)\
                                if ctx.pure_conds else inv_local_var
                # Store state before loop body
                pre_locals = self._local_variable_snapshot(ctx)
                pre_loop_iteration_conds = ctx.pure_conds
                # Loop Body
                with ctx.break_scope():
                    with ctx.continue_scope():
                        with self.assignment_translator.assume_everything_has_wrapped_information():
                            with ctx.new_local_scope():
                                self.translate_stmts(node.body, res, ctx)
                        ctx.pure_conds = pre_loop_iteration_conds
                        # After loop body increase idx
                        loop_idx_inc = self.viper_ast.Add(loop_idx_local_var, self.viper_ast.IntLit(1), pos)
                        loop_idx_var.new_idx()
                        loop_idx_local_var = loop_idx_var.local_var(ctx)
                        res.append(self.viper_ast.EqCmp(loop_idx_local_var, loop_idx_inc, pos))
                        # Break if we reached the end of the array we iterate over
                        loop_idx_eq_times = self.viper_ast.EqCmp(loop_idx_local_var, times_lit, pos)
                        cond_var = TranslatedPureIndexedVar('cond', 'cond', VYPER_BOOL, self.viper_ast, pos)
                        cond_local_var = cond_var.local_var(ctx)
                        res.append(self.viper_ast.EqCmp(cond_local_var, loop_idx_eq_times, pos))
                        break_cond = self.viper_ast.And(ctx.pure_conds, cond_local_var, pos)\
                            if ctx.pure_conds else cond_local_var
                        ctx.pure_breaks.append((break_cond, self._local_variable_snapshot(ctx)))

                    # Assume that only one of the breaks happened
                    only_one_break_cond = self._xor_conds([x for x, _ in ctx.pure_breaks])
                    assert only_one_break_cond is not None
                    if pre_conds is None:
                        res.append(only_one_break_cond)
                    else:
                        res.append(self.viper_ast.Implies(pre_conds, only_one_break_cond))
                    # Merge snapshots
                    prev_snapshot = pre_locals
                    for cond, snapshot in reversed(ctx.pure_breaks):
                        prev_snapshot = self._merge_snapshots(cond, snapshot, prev_snapshot, res, ctx)
            else:
                # Unroll loop if we have no loop invariants
                pre_loop_locals = self._local_variable_snapshot(ctx)
                with ctx.break_scope():
                    for i in range(times):
                        pre_loop_iteration_conds = ctx.pure_conds
                        with ctx.continue_scope():
                            idx = self.viper_ast.IntLit(i, lpos)
                            array_at = self.viper_ast.SeqIndex(array_local_var, idx, rpos)
                            if has_numeric_array:
                                array_at = helpers.w_wrap(self.viper_ast, array_at)
                            loop_var.new_idx()
                            var_set = self.viper_ast.EqCmp(loop_var.local_var(ctx), array_at, lpos)
                            res.append(var_set)

                            pre_it_locals = self._local_variable_snapshot(ctx)
                            with self.assignment_translator.assume_everything_has_wrapped_information():
                                with ctx.new_local_scope():
                                    self.translate_stmts(node.body, res, ctx)

                            post_it_locals = self._local_variable_snapshot(ctx)
                            ctx.pure_continues.append((ctx.pure_conds, post_it_locals))

                            prev_snapshot = pre_it_locals
                            for cond, snapshot in reversed(ctx.pure_continues):
                                prev_snapshot = self._merge_snapshots(cond, snapshot, prev_snapshot, res, ctx)

                        ctx.pure_conds = pre_loop_iteration_conds

                    post_loop_locals = self._local_variable_snapshot(ctx)
                    ctx.pure_breaks.append((ctx.pure_conds, post_loop_locals))

                    prev_snapshot = pre_loop_locals
                    for cond, snapshot in reversed(ctx.pure_breaks):
                        prev_snapshot = self._merge_snapshots(cond, snapshot, prev_snapshot, res, ctx)
        ctx.pure_conds = pre_conds

    def translate_Break(self, node: ast.Break, res: List[Expr], ctx: Context):
        ctx.pure_breaks.append((ctx.pure_conds, self._local_variable_snapshot(ctx)))
        ctx.pure_conds = self.viper_ast.FalseLit()

    def translate_Continue(self, node: ast.Continue, res: List[Expr], ctx: Context):
        ctx.pure_continues.append((ctx.pure_conds, self._local_variable_snapshot(ctx)))
        ctx.pure_conds = self.viper_ast.FalseLit()

    def translate_Pass(self, node: ast.Pass, res: List[Expr], ctx: Context):
        pass

    def _add_local_var(self, node: ast.Name, ctx: Context):
        """
        Adds the local variable to the context.
        """
        pos = self.to_position(node, ctx)
        variable_name = node.id
        mangled_name = ctx.new_local_var_name(variable_name)
        var = TranslatedPureIndexedVar(variable_name, mangled_name, node.type, self.viper_ast, pos)
        ctx.locals[variable_name] = var

    def _xor_conds(self, conds: List[Expr]) -> Optional[Expr]:
        xor_cond = None
        for i in range(len(conds)):
            prev = None
            for idx, cond in enumerate(conds):
                and_cond = cond if idx == i else self.viper_ast.Not(cond)
                prev = self.viper_ast.And(prev, and_cond) if prev else and_cond
            xor_cond = self.viper_ast.Or(xor_cond, prev) if xor_cond else prev
        return xor_cond

    @staticmethod
    def _local_variable_snapshot(ctx) -> LocalVarSnapshot:
        return dict(((name, (var.evaluate_idx(ctx), var.local_var(ctx), var.is_local))
                     for name, var in ctx.locals.items()
                     if isinstance(var, TranslatedPureIndexedVar)))

    @staticmethod
    def _reset_variable_to_snapshot(snapshot: LocalVarSnapshot, ctx):
        for name in snapshot.keys():
            var = ctx.locals[name]
            assert isinstance(var, TranslatedPureIndexedVar)
            var.idx, _, var.is_local = snapshot[name]

    def _merge_snapshots(self, merge_cond: Optional[Expr], first_snapshot: LocalVarSnapshot,
                         second_snapshot: LocalVarSnapshot, res: List[Expr], ctx: Context) -> LocalVarSnapshot:
        res_snapshot = {}
        names = set(first_snapshot.keys()) | set(second_snapshot.keys())
        for name in names:
            first_idx_and_var = first_snapshot.get(name)
            second_idx_and_var = second_snapshot.get(name)
            if first_idx_and_var and second_idx_and_var:
                then_idx, then_var, then_is_local = first_idx_and_var
                else_idx, else_var, else_is_local = second_idx_and_var
                var = ctx.locals[name]
                assert isinstance(var, TranslatedPureIndexedVar)
                if else_idx != then_idx:
                    var.new_idx()
                    var.is_local = then_is_local and else_is_local
                    cond = merge_cond or self.viper_ast.TrueLit()
                    expr = self.viper_ast.CondExp(cond, then_var, else_var)
                    assign = self.viper_ast.EqCmp(var.local_var(ctx), expr)
                    res.append(assign)
                res_snapshot[name] = (var.evaluate_idx(ctx), var.local_var(ctx), var.is_local)
            else:
                res_snapshot[name] = first_idx_and_var or second_idx_and_var
        return res_snapshot


class _AssignmentTranslator(PureTranslatorMixin, AssignmentTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.expression_translator = PureExpressionTranslator(viper_ast)
        self.type_translator = PureTypeTranslator(viper_ast)

    @property
    def method_name(self) -> str:
        return 'assign_to'

    def assign_to(self, node: ast.Node, value: Expr, res: List[Expr], ctx: Context):
        return self.visit(node, value, res, ctx)

    def generic_visit(self, node, *args):
        assert False

    def assign_to_Name(self, node: ast.Name, value: Expr, res: List[Expr], ctx: Context):
        pos = self.to_position(node, ctx)
        var = ctx.locals.get(node.id)
        w_value = value
        if var:
            if isinstance(var, TranslatedPureIndexedVar):
                var.new_idx()
            if (types.is_numeric(node.type)
                    and not var.is_local
                    and self.expression_translator.arithmetic_translator.is_unwrapped(value)):
                w_value = helpers.w_wrap(self.viper_ast, value)
            elif (types.is_numeric(node.type)
                    and var.is_local
                    and self.expression_translator.arithmetic_translator.is_wrapped(value)):
                var.is_local = False
            elif (types.is_numeric(node.type)
                    and self._always_wrap
                    and var.is_local
                    and self.expression_translator.arithmetic_translator.is_unwrapped(value)):
                var.is_local = False
                w_value = helpers.w_wrap(self.viper_ast, value)
            elif (not types.is_numeric(node.type)
                    and self.expression_translator.arithmetic_translator.is_wrapped(value)):
                w_value = helpers.w_unwrap(self.viper_ast, value)
        lhs = self.expression_translator.translate(node, res, ctx)
        assign = self.viper_ast.EqCmp(lhs, w_value, pos)
        expr = self.viper_ast.Implies(ctx.pure_conds, assign, pos) if ctx.pure_conds else assign
        res.append(expr)

    def assign_to_Attribute(self, node: ast.Attribute, value: Expr, res: List[Expr], ctx: Context):
        assert isinstance(node.value.type, StructType)
        return super().assign_to_Attribute(node, value, res, ctx)

    def assign_to_ReceiverCall(self, node: ast.ReceiverCall, value, ctx: Context):
        raise UnsupportedException(node, "Assignments to calls are not supported.")
