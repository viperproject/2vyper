"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import List

from nagini_translation.utils import flatten

from nagini_translation.ast import types
from nagini_translation.ast import names

from nagini_translation.ast.types import MapType, ArrayType

from nagini_translation.translation.context import Context, break_scope, continue_scope
from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.special import SpecialTranslator

from nagini_translation.translation.builtins import array_set, map_set

from nagini_translation.viper.ast import ViperAST
from nagini_translation.viper.typedefs import Stmt


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

        # An annotated assignment can only have a local variable on the lhs,
        # therefore we can simply use the expression translator
        lhs_stmts, lhs = self.expression_translator.translate(node.target, ctx)

        if node.value is None:
            type = node.target.type
            rhs_stmts, rhs = self.type_translator.default_value(None, type, ctx)
        else:
            rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)

        return lhs_stmts + rhs_stmts + [self.viper_ast.LocalVarAssign(lhs, rhs, pos)]

    def translate_Assign(self, node: ast.Assign, ctx: Context) -> List[Stmt]:
        # We only support single assignments for now
        left = node.targets[0]
        rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)
        assign_stmts, assign = self.assignment_translator.assign_to(left, rhs, ctx)
        return assign_stmts + rhs_stmts + [assign]

    def translate_AugAssign(self, node: ast.AugAssign, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        left = node.target

        lhs_stmts, lhs = self.expression_translator.translate(node.target, ctx)
        op = self.expression_translator.translate_operator(node.op)
        rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)

        stmts = lhs_stmts + rhs_stmts

        # If the divisor is 0 revert the transaction
        if isinstance(node.op, ast.Div) or isinstance(node.op, ast.Mod):
            cond = self.viper_ast.EqCmp(rhs, self.viper_ast.IntLit(0, pos), pos)
            stmts.append(self.fail_if(cond, ctx, pos))

        # If the result of a uint subtraction is negative, revert the transaction
        if isinstance(node.op, ast.Sub) and types.is_unsigned(left.type):
            cond = self.viper_ast.GtCmp(rhs, lhs, pos)
            stmts.append(self.fail_if(cond, ctx, pos))

        value = op(lhs, rhs, pos)

        assign_stmts, assign = self.assignment_translator.assign_to(node.target, value, ctx)
        return stmts + assign_stmts + [assign]

    def translate_Expr(self, node: ast.Expr, ctx: Context) -> List[Stmt]:
        # Check if we are translating a call to clear
        # We handle clear in the StatementTranslator because it is essentially an assignment
        is_call = lambda n: isinstance(n, ast.Call)
        is_clear = lambda n: isinstance(n, ast.Name) and n.id == names.CLEAR
        if is_call(node.value) and is_clear(node.value.func):
            arg = node.value.args[0]
            stmts, value = self.type_translator.default_value(node, arg.type, ctx)
            assign_stmts, assign = self.assignment_translator.assign_to(arg, value, ctx)
            return assign_stmts + stmts + [assign]
        else:
            # Ignore the expression, return the stmts
            stmts, _ = self.expression_translator.translate(node.value, ctx)
            return stmts

    def translate_Assert(self, node: ast.Assert, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        stmts, expr = self.expression_translator.translate(node.test, ctx)
        cond = self.viper_ast.Not(expr, pos)
        return stmts + [self.fail_if(cond, ctx, pos)]

    def translate_Return(self, node: ast.Return, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        jmp_to_end = self.viper_ast.Goto(ctx.end_label, pos)

        if node.value:
            stmts, expr = self.expression_translator.translate(node.value, ctx)
            result_var = ctx.result_var
            assign = self.viper_ast.LocalVarAssign(result_var.localVar(), expr, pos)
            return stmts + [assign, jmp_to_end]
        else:
            return [jmp_to_end]

    def translate_If(self, node: ast.If, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        cond_stmts, cond = self.expression_translator.translate(node.test, ctx)
        then_body = self.translate_stmts(node.body, ctx)
        else_body = self.translate_stmts(node.orelse, ctx)
        if_stmt = self.viper_ast.If(cond, then_body, else_body, pos)
        return cond_stmts + [if_stmt]

    def translate_For(self, node: ast.For, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        if not self.special_translator.is_range(node.iter):
            # TODO:
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
        # TODO:
        raise AssertionError(f"Node of type {type(node)} not supported.")

    def assign_to_Name(self, node: ast.Name, value, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        lhs_stmts, lhs = self.expression_translator.translate(node, ctx)
        assign = self.viper_ast.LocalVarAssign(lhs, value, pos)
        return lhs_stmts, assign

    def assign_to_Attribute(self, node: ast.Attribute, value, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        lhs_stmts, lhs = self.expression_translator.translate(node, ctx)
        assign = self.viper_ast.FieldAssign(lhs, value, pos)
        return lhs_stmts, assign

    def assign_to_Subscript(self, node: ast.Attribute, value, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        receiver_stmts, receiver = self.expression_translator.translate(node.value, ctx)
        index_stmts, index = self.expression_translator.translate(node.slice.value, ctx)
        stmts = []

        type = node.value.type
        if isinstance(type, MapType):
            key_type = self.type_translator.translate(type.key_type, ctx)
            value_type = self.type_translator.translate(type.value_type, ctx)
            new_value = map_set(self.viper_ast, receiver, index, value, key_type, value_type, pos)
        elif isinstance(type, ArrayType):
            stmts.append(self.type_translator.array_bounds_check(receiver, index, ctx))
            new_value = array_set(self.viper_ast, receiver, index, value, type.element_type, pos)
        else:
            assert False  # TODO: handle

        # We simply evaluate the receiver and index statements here, even though they
        # might get evaluated again in the recursive call. This is ok as long as the lhs of the
        # assignment is pure.
        assign_stmts, assign = self.assign_to(node.value, new_value, ctx)
        return receiver_stmts + index_stmts + stmts + assign_stmts, assign
