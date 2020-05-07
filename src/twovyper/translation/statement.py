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

from twovyper.translation import helpers
from twovyper.translation.context import Context
from twovyper.translation.abstract import NodeTranslator, CommonTranslator
from twovyper.translation.arithmetic import ArithmeticTranslator
from twovyper.translation.expression import ExpressionTranslator
from twovyper.translation.model import ModelTranslator
from twovyper.translation.specification import SpecificationTranslator
from twovyper.translation.type import TypeTranslator
from twovyper.translation.variable import TranslatedVar

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


class StatementTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast
        self.expression_translator = ExpressionTranslator(viper_ast)
        self.assignment_translator = _AssignmentTranslator(viper_ast)
        self.arithmetic_translator = ArithmeticTranslator(viper_ast)
        self.model_translator = ModelTranslator(viper_ast)
        self.specification_translator = SpecificationTranslator(viper_ast)
        self.type_translator = TypeTranslator(viper_ast)

    def translate_stmts(self, stmts: List[ast.Stmt], res: List[Stmt], ctx: Context):
        for s in stmts:
            self.translate(s, res, ctx)

    def translate_AnnAssign(self, node: ast.AnnAssign, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)

        self._add_local_var(node.target, ctx)

        # An annotated assignment can only have a local variable on the lhs,
        # therefore we can simply use the expression translator
        lhs = self.expression_translator.translate(node.target, res, ctx)

        if node.value is None:
            type = node.target.type
            rhs = self.type_translator.default_value(None, type, res, ctx)
        else:
            rhs = self.expression_translator.translate(node.value, res, ctx)

        res.append(self.viper_ast.LocalVarAssign(lhs, rhs, pos))

    def translate_Assign(self, node: ast.Assign, res: List[Stmt], ctx: Context):
        # We only support single assignments for now
        rhs = self.expression_translator.translate(node.value, res, ctx)
        self.assignment_translator.assign_to(node.target, rhs, res, ctx)

    def translate_AugAssign(self, node: ast.AugAssign, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)

        lhs = self.expression_translator.translate(node.target, res, ctx)
        rhs = self.expression_translator.translate(node.value, res, ctx)

        value = self.arithmetic_translator.arithmetic_op(lhs, node.op, rhs, node.value.type, res, ctx, pos)

        self.assignment_translator.assign_to(node.target, value, res, ctx)

    def translate_ExprStmt(self, node: ast.ExprStmt, res: List[Stmt], ctx: Context):
        # Check if we are translating a call to clear
        # We handle clear in the StatementTranslator because it is essentially an assignment
        if isinstance(node.value, ast.FunctionCall) and node.value.name == names.CLEAR:
            arg = node.value.args[0]
            value = self.type_translator.default_value(node, arg.type, res, ctx)
            self.assignment_translator.assign_to(arg, value, res, ctx)
        else:
            # Ignore the expression, return the stmts
            _ = self.expression_translator.translate(node.value, res, ctx)

    def translate_Raise(self, node: ast.Raise, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)

        # If UNREACHABLE is used, we assert that the exception is unreachable,
        # i.e., that it never happens; else, we revert
        if isinstance(node.msg, ast.Name) and node.msg.id == names.UNREACHABLE:
            modelt = self.model_translator.save_variables(res, ctx, pos)
            mpos = self.to_position(node, ctx, modelt=modelt)
            false = self.viper_ast.FalseLit(pos)
            res.append(self.viper_ast.Assert(false, mpos))
        else:
            res.append(self.viper_ast.Goto(ctx.revert_label, pos))

    def translate_Assert(self, node: ast.Assert, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)

        translator = self.specification_translator if node.is_ghost_code else self.expression_translator
        expr = translator.translate(node.test, res, ctx)

        # If UNREACHABLE is used, we try to prove that the assertion holds by
        # translating it directly as an assert; else, revert if the condition
        # is false.
        if isinstance(node.msg, ast.Name) and node.msg.id == names.UNREACHABLE:
            modelt = self.model_translator.save_variables(res, ctx, pos)
            mpos = self.to_position(node, ctx, modelt=modelt)
            res.append(self.viper_ast.Assert(expr, mpos))
        else:
            cond = self.viper_ast.Not(expr, pos)
            self.fail_if(cond, [], res, ctx, pos)

    def translate_Return(self, node: ast.Return, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)

        if node.value:
            expr = self.expression_translator.translate(node.value, res, ctx)
            assign = self.viper_ast.LocalVarAssign(ctx.result_var.local_var(ctx, pos), expr, pos)
            res.append(assign)

        res.append(self.viper_ast.Goto(ctx.return_label, pos))

    def translate_If(self, node: ast.If, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)

        translator = self.specification_translator if node.is_ghost_code else self.expression_translator
        cond = translator.translate(node.test, res, ctx)
        then_body = []
        self.translate_stmts(node.body, then_body, ctx)
        else_body = []
        self.translate_stmts(node.orelse, else_body, ctx)
        if_stmt = self.viper_ast.If(cond, then_body, else_body, pos)
        res.append(if_stmt)

    def translate_For(self, node: ast.For, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)

        self._add_local_var(node.target, ctx)

        # TODO: use loop invariants
        with ctx.break_scope():
            loop_var = ctx.all_vars[node.target.id].local_var(ctx)
            lpos = self.to_position(node.target, ctx)
            rpos = self.to_position(node.iter, ctx)

            times = node.iter.type.size
            array = self.expression_translator.translate(node.iter, res, ctx)

            for i in range(times):
                with ctx.continue_scope():
                    loop_info = self.to_info(["Start of loop iteration."])
                    idx = self.viper_ast.IntLit(i, lpos)
                    array_at = self.viper_ast.SeqIndex(array, idx, rpos)
                    var_set = self.viper_ast.LocalVarAssign(loop_var, array_at, lpos, loop_info)
                    res.append(var_set)
                    self.translate_stmts(node.body, res, ctx)
                    continue_info = self.to_info(["End of loop iteration."])
                    res.append(self.viper_ast.Label(ctx.continue_label, pos, continue_info))

            break_info = self.to_info(["End of loop."])
            res.append(self.viper_ast.Label(ctx.break_label, pos, break_info))

    def translate_Break(self, node: ast.Break, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)
        res.append(self.viper_ast.Goto(ctx.break_label, pos))

    def translate_Continue(self, node: ast.Continue, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)
        res.append(self.viper_ast.Goto(ctx.continue_label, pos))

    def translate_Pass(self, node: ast.Pass, res: List[Stmt], ctx: Context):
        pass

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

    def assign_to(self, node: ast.Node, value: Expr, res: List[Stmt], ctx: Context):
        return self.visit(node, value, res, ctx)

    def generic_visit(self, node: ast.Node, value: Expr, res: List[Stmt], ctx: Context):
        assert False

    def assign_to_Name(self, node: ast.Name, value: Expr, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)
        lhs = self.expression_translator.translate(node, res, ctx)
        res.append(self.viper_ast.LocalVarAssign(lhs, value, pos))

    def assign_to_Attribute(self, node: ast.Attribute, value: Expr, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)
        if isinstance(node.value.type, StructType):
            rec = self.expression_translator.translate(node.value, res, ctx)
            type = self.type_translator.translate(node.type, ctx)
            new_value = helpers.struct_set(self.viper_ast, rec, value, node.attr, type, node.value.type, pos)
            self.assign_to(node.value, new_value, res, ctx)
        else:
            lhs = self.expression_translator.translate(node, res, ctx)
            res.append(self.viper_ast.FieldAssign(lhs, value, pos))

    def assign_to_Subscript(self, node: ast.Subscript, value: Expr, res: List[Stmt], ctx: Context):
        pos = self.to_position(node, ctx)

        receiver = self.expression_translator.translate(node.value, res, ctx)
        index = self.expression_translator.translate(node.index, res, ctx)

        type = node.value.type
        if isinstance(type, MapType):
            key_type = self.type_translator.translate(type.key_type, ctx)
            value_type = self.type_translator.translate(type.value_type, ctx)
            new_value = helpers.map_set(self.viper_ast, receiver, index, value, key_type, value_type, pos)
        elif isinstance(type, ArrayType):
            self.type_translator.array_bounds_check(receiver, index, res, ctx)
            new_value = helpers.array_set(self.viper_ast, receiver, index, value, type.element_type, pos)
        else:
            assert False

        # We simply evaluate the receiver and index statements here, even though they
        # might get evaluated again in the recursive call. This is ok as long as the lhs of the
        # assignment is pure.
        self.assign_to(node.value, new_value, res, ctx)

    def assign_to_ReceiverCall(self, node: ast.ReceiverCall, value, ctx: Context):
        raise UnsupportedException(node, "Assignments to calls are not supported.")
