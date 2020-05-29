"""
Copyright (c) 2020 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Dict, Tuple

from twovyper.ast import ast_nodes as ast
from twovyper.ast.types import StructType, VYPER_BOOL

from twovyper.exceptions import UnsupportedException

from twovyper.translation import helpers
from twovyper.translation.context import Context
from twovyper.translation.pure_translators import PureTranslatorMixin, PureExpressionTranslator, \
    PureArithmeticTranslator, PureSpecificationTranslator, PureTypeTranslator
from twovyper.translation.statement import AssignmentTranslator, StatementTranslator
from twovyper.translation.variable import TranslatedPureIndexedVar

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt, Var


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
        else:
            rhs = self.expression_translator.translate(node.value, res, ctx)

        lhs.new_idx()
        assign = self.viper_ast.EqCmp(lhs.local_var(ctx, pos), rhs, pos)
        res.append(assign)

    def translate_Raise(self, node: ast.Raise, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)
        self.fail_if(self.viper_ast.TrueLit(), [], res, ctx, pos)

    def translate_Assert(self, node: ast.Assert, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)
        expr = self.expression_translator.translate(node.test, res, ctx)
        cond = self.viper_ast.Not(expr, pos)
        self.fail_if(cond, [], res, ctx, pos)

    def translate_Return(self, node: ast.Return, res: List[Stmt], ctx: Context):
        assert node.value
        assert isinstance(ctx.result_var, TranslatedPureIndexedVar)
        assert isinstance(ctx.success_var, TranslatedPureIndexedVar)
        pos = self.to_position(node, ctx)

        expr = self.expression_translator.translate(node.value, res, ctx)

        ctx.result_var.new_idx()
        assign = self.viper_ast.EqCmp(ctx.result_var.local_var(ctx), expr, pos)
        res.append(assign)
        if ctx.pure_conds:
            ctx.pure_returns.append((ctx.pure_conds, ctx.result_var.evaluate_idx(ctx)))
            ctx.pure_success.append((ctx.pure_conds, ctx.success_var.evaluate_idx(ctx)))
        else:
            ctx.pure_returns.append((self.viper_ast.TrueLit(), ctx.result_var.evaluate_idx(ctx)))
            ctx.pure_success.append((self.viper_ast.TrueLit(), ctx.success_var.evaluate_idx(ctx)))

    def translate_If(self, node: ast.If, res: List[Stmt], ctx: Context):
        pre_locals = self._local_variable_snapshot(ctx)
        pre_conds = ctx.pure_conds

        pos = self.to_position(node, ctx)
        cond = self.expression_translator.translate(node.test, res, ctx)

        cond_var = TranslatedPureIndexedVar('cond', 'cond', VYPER_BOOL, self.viper_ast, pos)
        res.append(self.viper_ast.EqCmp(cond_var.local_var(ctx), cond))
        cond_local_var = cond_var.local_var(ctx)

        # "Then" branch
        with ctx.new_local_scope():
            # Update condition
            ctx.pure_conds = self.viper_ast.And(pre_conds, cond_local_var) if pre_conds else cond_local_var
            self.translate_stmts(node.body, res, ctx)
            # Get current state of local variable state after "then"-branch
            then_locals = self._local_variable_snapshot(ctx)
        # Reset indices of local variables in context
        self._reset_variable_to_snapshot(pre_locals, ctx)
        # "Else" branch
        with ctx.new_local_scope():
            # Update condition
            negated_local_var = self.viper_ast.Not(cond_local_var)
            ctx.pure_conds = self.viper_ast.And(pre_conds, negated_local_var) if pre_conds else negated_local_var
            self.translate_stmts(node.orelse, res, ctx)
            # Get current state of local variable state after "else"-branch
            else_locals = self._local_variable_snapshot(ctx)
        # Reset indices of local variables in context
        self._reset_variable_to_snapshot(pre_locals, ctx)
        # Update condition
        ctx.pure_conds = pre_conds
        # Merge variable changed in the "then" or "else" branch
        for name in pre_locals.keys():
            else_idx, else_var = else_locals[name]
            then_idx, then_var = then_locals[name]
            if else_idx != then_idx:
                var = ctx.locals[name]
                assert isinstance(var, TranslatedPureIndexedVar)
                var.new_idx()
                expr = self.viper_ast.CondExp(cond_local_var, then_var, else_var, pos)
                assign = self.viper_ast.EqCmp(var.local_var(ctx), expr, pos)
                res.append(assign)

    def translate_For(self, node: ast.For, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)

        self._add_local_var(node.target, ctx)
        loop_var = ctx.locals[node.target.id]
        assert isinstance(loop_var, TranslatedPureIndexedVar)
        array = self.expression_translator.translate(node.iter, res, ctx)
        array_var = TranslatedPureIndexedVar('array', 'array', node.iter.type, self.viper_ast, pos)
        res.append(self.viper_ast.EqCmp(array_var.local_var(ctx), array))
        array_local_var = array_var.local_var(ctx)

        times = node.iter.type.size
        lpos = self.to_position(node.target, ctx)
        rpos = self.to_position(node.iter, ctx)

        if times > 0:
            loop_invariants = ctx.function.loop_invariants.get(node)
            if loop_invariants:
                assert False
            else:
                pre_locals = self._local_variable_snapshot(ctx)
                pre_conds = ctx.pure_conds
                with ctx.break_scope():
                    for i in range(times):
                        with ctx.continue_scope():
                            idx = self.viper_ast.IntLit(i, lpos)
                            array_at = self.viper_ast.SeqIndex(array_local_var, idx, rpos)
                            loop_var.new_idx()
                            var_set = self.viper_ast.EqCmp(loop_var.local_var(ctx), array_at, lpos)
                            res.append(var_set)

                            with ctx.new_local_scope():
                                self.translate_stmts(node.body, res, ctx)

                            post_it_locals = self._local_variable_snapshot(ctx)

                            prev_snapshot = post_it_locals
                            for cond, snapshot in reversed(ctx.pure_continues):
                                for name in snapshot.keys():
                                    else_idx, else_var = prev_snapshot[name]
                                    then_idx, then_var = snapshot[name]
                                    if else_idx != then_idx:
                                        var = ctx.locals[name]
                                        assert isinstance(var, TranslatedPureIndexedVar)
                                        var.new_idx()
                                        expr = self.viper_ast.CondExp(cond, then_var, else_var, pos)
                                        assign = self.viper_ast.EqCmp(var.local_var(ctx), expr, pos)
                                        res.append(assign)
                                        snapshot[name] = (var.evaluate_idx(ctx), var.local_var(ctx))
                                prev_snapshot = snapshot

                    prev_snapshot = pre_locals
                    for cond, snapshot in reversed(ctx.pure_breaks):
                        for name in prev_snapshot.keys():
                            else_idx, else_var = prev_snapshot[name]
                            then_idx, then_var = snapshot[name]
                            if else_idx != then_idx:
                                var = ctx.locals[name]
                                assert isinstance(var, TranslatedPureIndexedVar)
                                var.new_idx()
                                expr = self.viper_ast.CondExp(cond, then_var, else_var, pos)
                                assign = self.viper_ast.EqCmp(var.local_var(ctx), expr, pos)
                                res.append(assign)
                                snapshot[name] = (var.evaluate_idx(ctx), var.local_var(ctx))
                        prev_snapshot = snapshot
                ctx.pure_conds = pre_conds

    def translate_Break(self, node: ast.Break, res: List[Stmt], ctx: Context):
        ctx.pure_breaks.append((ctx.pure_conds, self._local_variable_snapshot(ctx)))

    def translate_Continue(self, node: ast.Continue, res: List[Stmt], ctx: Context):
        ctx.pure_continues.append((ctx.pure_conds, self._local_variable_snapshot(ctx)))

    def translate_Pass(self, node: ast.Pass, res: List[Stmt], ctx: Context):
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

    @staticmethod
    def _local_variable_snapshot(ctx) -> Dict[str, Tuple[int, Var]]:
        return dict(((name, (var.evaluate_idx(ctx), var.local_var(ctx)))
                     for name, var in
                     filter(lambda x: isinstance(x[1], TranslatedPureIndexedVar), ctx.locals.items())))

    @staticmethod
    def _reset_variable_to_snapshot(snapshot, ctx):
        for name in snapshot.keys():
            var = ctx.locals[name]
            assert isinstance(var, TranslatedPureIndexedVar)
            var.idx, _ = snapshot[name]


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
        if var and isinstance(var, TranslatedPureIndexedVar):
            var.new_idx()
        lhs = self.expression_translator.translate(node, res, ctx)
        assign = self.viper_ast.EqCmp(lhs, value, pos)
        res.append(assign)

    def assign_to_Attribute(self, node: ast.Attribute, value: Expr, res: List[Expr], ctx: Context):
        assert isinstance(node.value.type, StructType)
        return super().assign_to_Attribute(node, value, res, ctx)

    def assign_to_ReceiverCall(self, node: ast.ReceiverCall, value, ctx: Context):
        raise UnsupportedException(node, "Assignments to calls are not supported.")
