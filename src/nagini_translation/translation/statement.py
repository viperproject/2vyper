"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import List

from nagini_translation.utils import flatten
from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import Stmt

from nagini_translation.ast import types

from nagini_translation.translation.context import Context, break_scope, continue_scope
from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.special import SpecialTranslator

from nagini_translation.translation.builtins import map_set


class StatementTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.assignment_translator = _AssignmentTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)
        self.special_translator = SpecialTranslator(viper_ast)

    def translate_stmts(self, stmts: List[Stmt], ctx: Context) -> List[Stmt]:
        return flatten([self.translate(s, ctx) for s in stmts])

    def translate_AnnAssign(self, node: ast.AnnAssign, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        # An annotated assignment can only have a local variable on the lhs,
        # therefore we can simply use the expression translator
        lhs_stmts, lhs = self.expression_translator.translate(node.target, ctx)

        if node.value is None:
            type = node.target.type
            rhs_stmts, rhs = self.type_translator.default_value(type, ctx)
        else:
            rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)

        return lhs_stmts + rhs_stmts + [self.viper_ast.LocalVarAssign(lhs, rhs, pos)]

    def translate_Assign(self, node: ast.Assign, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        # We only support single assignments for now
        left = node.targets[0]
        rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)
        return self.assignment_translator.assign_to(left, rhs, ctx) + rhs_stmts

    def translate_AugAssign(self, node: ast.AugAssign, ctx: Context) -> List[Stmt]:
        # TODO: combine with normal assign?
        pos = self.to_position(node, ctx)

        left = node.target

        lhs_stmts, lhs = self.expression_translator.translate(node.target, ctx)
        op = self.expression_translator.translate_operator(node.op)
        rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)

        stmts = lhs_stmts + rhs_stmts

        def fail_if(cond):
            body = [self.viper_ast.Goto(ctx.revert_label, pos)]
            block = self.viper_ast.Seqn(body, pos)
            empty = self.viper_ast.Seqn([], pos)
            return self.viper_ast.If(cond, block, empty, pos)

        # If the divisor is 0 revert the transaction
        if isinstance(node.op, ast.Div) or isinstance(node.op, ast.Mod):
            cond = self.viper_ast.EqCmp(rhs, self.viper_ast.IntLit(0, pos), pos)
            stmts.append(fail_if(cond))

        # If the result of a uint subtraction is negative, revert the transaction
        if isinstance(node.op, ast.Sub) and left.type == types.VYPER_UINT256:
            cond = self.viper_ast.GtCmp(rhs, lhs, pos)
            stmts.append(fail_if(cond))

        value = op(lhs, rhs, pos)
        return stmts + self.assignment_translator.assign_to(node.target, value, ctx)

    def translate_Assert(self, node: ast.Assert, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        stmts, expr = self.expression_translator.translate(node.test, ctx)
        
        cond = self.viper_ast.Not(expr, pos)
        body = [self.viper_ast.Goto(ctx.revert_label, pos)]
        block = self.viper_ast.Seqn(body, pos)
        empty = self.viper_ast.Seqn([], pos)
        if_stmt = self.viper_ast.If(cond, block, empty, pos)
        return stmts + [if_stmt]

    def translate_Return(self, node: ast.Return, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        stmts, expr = self.expression_translator.translate(node.value, ctx)
        result_var = ctx.result_var
        assign = self.viper_ast.LocalVarAssign(result_var.localVar(), expr, pos)
        jmp_to_end = self.viper_ast.Goto(ctx.end_label, pos)

        return stmts + [assign, jmp_to_end]

    def translate_If(self, node: ast.If, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        cond_stmts, cond = self.expression_translator.translate(node.test, ctx)
        then_body = self.translate_stmts(node.body, ctx)
        then_block = self.viper_ast.Seqn(then_body, pos)

        else_body = self.translate_stmts(node.orelse, ctx)
        else_block = self.viper_ast.Seqn(else_body, pos)
        if_stmt = self.viper_ast.If(cond, then_block, else_block, pos)
        return cond_stmts + [if_stmt]

    def translate_For(self, node: ast.For, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        if not self.special_translator.is_range(node.iter):
            raise AssertionError("Not supported yet")

        with break_scope(ctx):
            loop_var = ctx.all_vars[node.target.id].localVar()
            lpos = self.to_position(node.target, ctx)
            stmts, start, times = self.special_translator.translate_range(node.iter, ctx)
            init_info = self.to_info(["Loop variable initialization.\n"])
            var_init = self.viper_ast.LocalVarAssign(loop_var, start, lpos, init_info)
            stmts.append(var_init)
            plus = self.viper_ast.Add(loop_var, self.viper_ast.IntLit(1), lpos)
            var_inc = self.viper_ast.LocalVarAssign(loop_var, plus, lpos)

            for i in range(times):
                with continue_scope(ctx):
                    stmts += self.translate_stmts(node.body, ctx)
                    continue_info = self.to_info(["End of loop iteration.\n"])
                    stmts.append(self.viper_ast.Label(ctx.continue_label, pos, continue_info))
                    stmts.append(var_inc)

            stmts += self.translate_stmts(node.orelse, ctx)
            break_info = self.to_info(["End of loop.\n"])
            stmts.append(self.viper_ast.Label(ctx.break_label, pos, break_info))
            return stmts

    def translate_Break(self, node: ast.Break, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        return [self.viper_ast.Goto(ctx.break_label, pos)]

    def translate_Continue(self, node: ast.Continue, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        return [self.viper_ast.Goto(ctx.continue_label, pos)]

    def translate_Pass(self, node: ast.Pass, ctx: Context) -> List[Stmt]:
        return []


class _AssignmentTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def assign_to(self, node, value, ctx):
        """Translate a node."""
        method = 'assign_to_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_assign_to)
        return visitor(node, value, ctx)

    def generic_assign_to(self, node, value, ctx):
        raise AssertionError(f"Node of type {type(node)} not supported.")

    def assign_to_Name(self, node: ast.Name, value, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        lhs_stmts, lhs = self.expression_translator.translate(node, ctx)
        assign = self.viper_ast.LocalVarAssign(lhs, value, pos)
        return lhs_stmts + [assign]

    def assign_to_Attribute(self, node: ast.Attribute, value, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        lhs_stmts, lhs = self.expression_translator.translate(node, ctx)
        assign = self.viper_ast.FieldAssign(lhs, value, pos)
        return lhs_stmts + [assign]

    def assign_to_Subscript(self, node: ast.Attribute, value, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        map_type = node.value.type
        key_type = self.type_translator.translate(map_type.key_type, ctx)
        value_type = self.type_translator.translate(map_type.value_type, ctx)

        receiver_stmts, receiver = self.expression_translator.translate(node.value, ctx)
        index_stmts, index = self.expression_translator.translate(node.slice.value, ctx)
        new_value = map_set(self.viper_ast, receiver, index, value, key_type, value_type, pos)

        # We simply evaluate the receiver and index statements here, even though they 
        # might get evaluated again in the recursive call. This is ok as long as the lhs of the
        # assignment is pure.
        return receiver_stmts + index_stmts + self.assign_to(node.value, new_value, ctx)
