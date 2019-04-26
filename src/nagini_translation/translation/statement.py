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
from nagini_translation.parsing.types import VYPER_INT128

from nagini_translation.translation.context import Context, break_scope, continue_scope
from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.expression import ExpressionTranslator
from nagini_translation.translation.type import TypeTranslator
from nagini_translation.translation.special import SpecialTranslator


class StatementTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.expression_translator = ExpressionTranslator(self.viper_ast)
        self.type_translator = TypeTranslator(viper_ast)
        self.special_translator = SpecialTranslator(viper_ast)

    def translate_stmts(self, stmts: List[Stmt], ctx: Context) -> List[Stmt]:
        return flatten([self.translate(s, ctx) for s in stmts])

    def translate_AnnAssign(self, node: ast.AnnAssign, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        info = self.no_info()
        lhs_stmts, lhs = self.expression_translator.translate(node.target, ctx)
        # TODO: put into own class default_value_translator?
        if node.value is None:
            rhs_ast = ast.parse(ctx.types[node.target.id].default_value, mode='eval').body
            rhs_stmts, rhs = self.expression_translator.translate(rhs_ast, ctx)
        else:
            rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)
        return lhs_stmts + rhs_stmts + [self.viper_ast.LocalVarAssign(lhs, rhs, pos, info)]

    def translate_Assign(self, node: ast.Assign, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        info = self.no_info()

        left = node.targets[0]
        lhs_stmts, lhs = self.expression_translator.translate(left, ctx)
        rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)

        if isinstance(left, ast.Name):
            assign = self.viper_ast.LocalVarAssign
        elif isinstance(left, ast.Attribute):
            assign = self.viper_ast.FieldAssign
        else:
            # TODO: allow assignments to other things
            assert False

        return lhs_stmts + rhs_stmts + [assign(lhs, rhs, pos, info)]

    def translate_AugAssign(self, node: ast.AugAssign, ctx: Context) -> List[Stmt]:
        #TODO: allow assignments to other things
        pos = self.to_position(node, ctx)
        info = self.no_info()

        lhs_stmts, lhs = self.expression_translator.translate(node.target, ctx)
        rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)
        op = self.expression_translator.translate_operator(node.op)
        assign = self.viper_ast.LocalVarAssign(lhs, op(lhs, rhs, pos, info), pos, info)
        
        return lhs_stmts + rhs_stmts + [assign]

    def translate_Return(self, node: ast.Return, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        info = self.no_info()

        stmts, expr = self.expression_translator.translate(node.value, ctx)
        result_var = ctx.result_var
        assign = self.viper_ast.LocalVarAssign(result_var.localVar(), expr, pos, info)
        jmp_to_end = self.viper_ast.Goto(ctx.end_label.name(), pos, info)

        return stmts + [assign, jmp_to_end]

    def translate_If(self, node: ast.If, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        info = self.no_info()

        cond_stmts, cond = self.expression_translator.translate(node.test, ctx)
        then_body = self.translate_stmts(node.body, ctx)
        then_block = self.viper_ast.Seqn(then_body, pos, info)

        else_body = self.translate_stmts(node.orelse, ctx)
        else_block = self.viper_ast.Seqn(else_body, pos, info)
        if_stmt = self.viper_ast.If(cond, then_block, else_block, pos, info)
        return cond_stmts + [if_stmt]

    def translate_For(self, node: ast.For, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        no_pos = self.no_position()
        info = self.no_info()

        if not self.special_translator.is_range(node.iter):
            raise AssertionError("Not supported yet")

        with break_scope(ctx):
            loop_var = ctx.all_vars[node.target.id].localVar()
            lpos = self.to_position(node, ctx.target)
            stmts, start, times = self.special_translator.translate_range(node.iter, ctx)
            init_info = self.to_info(["Loop variable initialization.\n"])
            var_init = self.viper_ast.LocalVarAssign(loop_var, start, lpos, init_info)
            stmts.append(var_init)
            plus = self.viper_ast.Add(loop_var, self.viper_ast.IntLit(1, no_pos, info), lpos, info)
            var_inc = self.viper_ast.LocalVarAssign(loop_var, plus, lpos, info)

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
        info = self.no_info()
        return [self.viper_ast.Goto(ctx.break_label, pos, info)]

    def translate_Continue(self, node: ast.Continue, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)
        info = self.no_info()
        return [self.viper_ast.Goto(ctx.continue_label, pos, info)]

    def translate_Pass(self, node: ast.Pass, ctx: Context) -> List[Stmt]:
        return []