"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from twovyper.ast import ast_nodes as ast, names
from twovyper.ast.types import MapType, ArrayType, StructType
from twovyper.ast.visitors import NodeVisitor

from twovyper.exceptions import UnsupportedException

from twovyper.utils import flatten

from twovyper.translation import helpers
from twovyper.translation.context import Context, break_scope, continue_scope
from twovyper.translation.abstract import NodeTranslator, CommonTranslator
from twovyper.translation.arithmetic import ArithmeticTranslator
from twovyper.translation.expression import ExpressionTranslator
from twovyper.translation.model import ModelTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Stmt


class StatementTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.assignment_translator = _AssignmentTranslator(viper_ast)
        self.arithmetic_translator = ArithmeticTranslator(viper_ast)
        self.model_translator = ModelTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def translate_stmts(self, stmts: List[Stmt], ctx: Context) -> List[Stmt]:
        return flatten([self.translate(s, ctx) for s in stmts])

    def translate_AnnAssign(self, node: ast.AnnAssign, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        self._add_local_var(node.target, ctx)

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
        rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)
        assign_stmts, assign = self.assignment_translator.assign_to(node.target, rhs, ctx)
        return assign_stmts + rhs_stmts + [assign]

    def translate_AugAssign(self, node: ast.AugAssign, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        lhs_stmts, lhs = self.expression_translator.translate(node.target, ctx)
        rhs_stmts, rhs = self.expression_translator.translate(node.value, ctx)

        at = self.arithmetic_translator
        value_stmts, value = at.arithmetic_op(lhs, node.op, rhs, node.value.type, ctx, pos)

        assign_stmts, assign = self.assignment_translator.assign_to(node.target, value, ctx)
        return [*lhs_stmts, *rhs_stmts, *value_stmts, *assign_stmts, assign]

    def translate_ExprStmt(self, node: ast.ExprStmt, ctx: Context) -> List[Stmt]:
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

    def translate_Raise(self, node: ast.Raise, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        # If UNREACHABLE is used, we assert that the exception is unreachable,
        # i.e., that it never happens; else, we revert
        if isinstance(node.msg, ast.Name) and node.msg.id == names.UNREACHABLE:
            save_vars, modelt = self.model_translator.save_variables(ctx, pos)
            mpos = self.to_position(node, ctx, modelt=modelt)
            false = self.viper_ast.FalseLit(pos)
            return [*save_vars, self.viper_ast.Assert(false, mpos)]
        else:
            return [self.viper_ast.Goto(ctx.revert_label, pos)]

    def translate_Assert(self, node: ast.Assert, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        stmts, expr = self.expression_translator.translate(node.test, ctx)

        # If UNREACHABLE is used, we try to prove that the assertion holds by
        # translating it directly as an assert; else, revert if the condition
        # is false.
        if isinstance(node.msg, ast.Name) and node.msg.id == names.UNREACHABLE:
            save_vars, modelt = self.model_translator.save_variables(ctx, pos)
            mpos = self.to_position(node, ctx, modelt=modelt)
            return stmts + save_vars + [self.viper_ast.Assert(expr, mpos)]
        else:
            cond = self.viper_ast.Not(expr, pos)
            return stmts + [self.fail_if(cond, [], ctx, pos)]

    def translate_Return(self, node: ast.Return, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        jmp_to_return = self.viper_ast.Goto(ctx.return_label, pos)

        if node.value:
            stmts, expr = self.expression_translator.translate(node.value, ctx)
            assign = self.viper_ast.LocalVarAssign(ctx.result_var.local_var(ctx, pos), expr, pos)
            return stmts + [assign, jmp_to_return]
        else:
            return [jmp_to_return]

    def translate_If(self, node: ast.If, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        cond_stmts, cond = self.expression_translator.translate(node.test, ctx)
        then_body = self.translate_stmts(node.body, ctx)
        else_body = self.translate_stmts(node.orelse, ctx)
        if_stmt = self.viper_ast.If(cond, then_body, else_body, pos)
        return cond_stmts + [if_stmt]

    def translate_For(self, node: ast.For, ctx: Context) -> List[Stmt]:
        pos = self.to_position(node, ctx)

        self._add_local_var(node.target, ctx)

        with break_scope(ctx):
            loop_var = ctx.all_vars[node.target.id].local_var(ctx)
            lpos = self.to_position(node.target, ctx)
            rpos = self.to_position(node.iter, ctx)

            times = node.iter.type.size
            stmts, array = self.expression_translator.translate(node.iter, ctx)

            for i in range(times):
                with continue_scope(ctx):
                    loop_info = self.to_info(["Start of loop iteration."])
                    idx = self.viper_ast.IntLit(i, lpos)
                    array_at = self.viper_ast.SeqIndex(array, idx, rpos)
                    var_set = self.viper_ast.LocalVarAssign(loop_var, array_at, lpos, loop_info)
                    stmts.append(var_set)
                    stmts.extend(self.translate_stmts(node.body, ctx))
                    continue_info = self.to_info(["End of loop iteration."])
                    stmts.append(self.viper_ast.Label(ctx.continue_label, pos, continue_info))

            break_info = self.to_info(["End of loop."])
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

    def _add_local_var(self, node: ast.Name, ctx: Context):
        """
        Adds the local variable to the context.
        """
        pos = self.to_position(node, ctx)
        variable_name = node.id
        mangled_name = ctx.new_local_var_name(variable_name)
        var = TranslatedVar(variable_name, mangled_name, node.type, self.viper_ast, pos)
        ctx.locals[variable_name] = var
        ctx.new_local_vars.append(var.var_decl(ctx))


class _AssignmentTranslator(NodeVisitor, CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    @property
    def method_name(self) -> str:
        return 'assign_to'

    def assign_to(self, node, value, ctx):
        return self.visit(node, value, ctx)

    def generic_visit(self, node, value, ctx):
        assert False

    def assign_to_Name(self, node: ast.Name, value, ctx: Context):
        pos = self.to_position(node, ctx)
        lhs_stmts, lhs = self.expression_translator.translate(node, ctx)
        assign = self.viper_ast.LocalVarAssign(lhs, value, pos)
        return lhs_stmts, assign

    def assign_to_Attribute(self, node: ast.Attribute, value, ctx: Context):
        pos = self.to_position(node, ctx)
        if isinstance(node.value.type, StructType):
            receiver_stmts, rec = self.expression_translator.translate(node.value, ctx)
            type = self.type_translator.translate(node.type, ctx)
            new_value = helpers.struct_set(self.viper_ast, rec, value, node.attr, type, node.value.type, pos)
            assign_stmts, assign = self.assign_to(node.value, new_value, ctx)
            return receiver_stmts + assign_stmts, assign
        else:
            lhs_stmts, lhs = self.expression_translator.translate(node, ctx)
            assign = self.viper_ast.FieldAssign(lhs, value, pos)
            return lhs_stmts, assign

    def assign_to_Subscript(self, node: ast.Subscript, value, ctx: Context):
        pos = self.to_position(node, ctx)

        receiver_stmts, receiver = self.expression_translator.translate(node.value, ctx)
        index_stmts, index = self.expression_translator.translate(node.index, ctx)
        stmts = []

        type = node.value.type
        if isinstance(type, MapType):
            key_type = self.type_translator.translate(type.key_type, ctx)
            value_type = self.type_translator.translate(type.value_type, ctx)
            new_value = helpers.map_set(self.viper_ast, receiver, index, value, key_type, value_type, pos)
        elif isinstance(type, ArrayType):
            stmts.append(self.type_translator.array_bounds_check(receiver, index, ctx))
            new_value = helpers.array_set(self.viper_ast, receiver, index, value, type.element_type, pos)
        else:
            assert False

        # We simply evaluate the receiver and index statements here, even though they
        # might get evaluated again in the recursive call. This is ok as long as the lhs of the
        # assignment is pure.
        assign_stmts, assign = self.assign_to(node.value, new_value, ctx)
        return receiver_stmts + index_stmts + stmts + assign_stmts, assign

    def assign_to_Call(self, node: ast.Call, value, ctx: Context):
        raise UnsupportedException(node, "Assignments to calls are not supported.")
