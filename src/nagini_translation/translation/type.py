"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

import nagini_translation.translation.builtins as builtins

from typing import Optional

from nagini_translation.parsing.types import *

from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.typedefs import Type, Expr, Stmt, StmtsAndExpr

from nagini_translation.translation.abstract import NodeTranslator
from nagini_translation.translation.context import Context
from nagini_translation.translation.builtins import map_type


class TypeTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)
        self.type_dict = {
            VYPER_BOOL: viper_ast.Bool, 
            VYPER_INT128: viper_ast.Int,
            VYPER_UINT256: viper_ast.Int, 
            VYPER_WEI_VALUE: viper_ast.Int,
            VYPER_ADDRESS: viper_ast.Int
        }
        self._type_visitor = _TypeVisitor(viper_ast)

    def translate(self, type: VyperType, ctx: Context) -> VyperType:
        if isinstance(type, PrimitiveType):
            return self.type_dict[type]
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)
            return map_type(self.viper_ast, key_type, value_type)
        else:
            return self.viper_ast.Ref

    def type_of(self, node: ast.AST, ctx: Context) -> VyperType:
        return self._type_visitor.type_of(node, ctx)

    # TODO: This method seems very weird, change it once more permissions are needed for other
    # types, else integrate it into translator
    def permissions(self, type: VyperType, field, ctx: Context) -> Optional[Expr]:
        pos = self.no_position()
        info = self.no_info()

        if isinstance(type, PrimitiveType):
            return None
        elif isinstance(type, MapType):
            return None
            field_acc = self.viper_ast.FieldAccess(ctx.self_var.localVar(), field, pos, info)
            return map_acc(self.viper_ast, field_acc, pos, info)
        else:
            # TODO: handle other?
            assert False

    def revert(self, type: VyperType, field, ctx: Context) -> [Stmt]:
        nopos = self.no_position()
        info = self.no_info()

        def old(ref, field):
            field_acc = self.viper_ast.FieldAccess(ref, field, nopos, info)
            old = self.viper_ast.Old(field_acc, nopos, info)
            return self.viper_ast.FieldAssign(field_acc, old, nopos, info)

        self_var = ctx.self_var.localVar()
        return [old(self_var, field)]

    def translate_default_value(self, type: VyperType, ctx: Context) -> StmtsAndExpr:
        pos = self.no_position()
        info = self.no_info()

        if type is VYPER_BOOL:
            return [], self.viper_ast.FalseLit(pos, info)
        elif isinstance(type, PrimitiveType):
            return [], self.viper_ast.IntLit(0, pos, info)
        elif isinstance(type, MapType):
            key_type = self.translate(type.key_type, ctx)
            value_type = self.translate(type.value_type, ctx)

            stmts, value_default = self.translate_default_value(type.value_type, ctx)
            call = builtins.map_init(self.viper_ast, value_default, key_type, value_type, pos, info)
            return [], call
        else:
            # TODO:
            assert False


class _TypeVisitor(NodeTranslator):

    def type_of(self, ast: ast.AST, ctx: Context) -> VyperType:
        return self.visit(ast, ctx)

    def visit(self, node, ctx):
        """Translate a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, ctx)

    def generic_visit(self, node, ctx):
        raise AssertionError(f"Node of type {type(node)} not supported.")

    def visit_BoolOp(self, node: ast.BoolOp, ctx: Context) -> VyperType:
        return VYPER_BOOL

    def visit_BinOp(self, node: ast.BinOp, ctx: Context) -> VyperType:
        return self.visit(node.left, ctx)

    def visit_UnaryOp(self, node: ast.UnaryOp, ctx: Context) -> VyperType:
        return self.visit(node.operand, ctx)

    def visit_Compare(self, node: ast.Compare, ctx: Context) -> VyperType:
        return VYPER_BOOL

    def visit_Call(self, node: ast.Call, ctx: Context) -> VyperType:
        if isinstance(node.func, ast.Name):
            if node.func.id == 'min' or node.func.id == 'max':
                return self.visit(node.args[0], ctx)
            else:
                raise AssertionError("Not supported.")
        else:
            return ctx.program.functions[node.func.value.id].ret

    def visit_Num(self, node: ast.Num, ctx: Context) -> VyperType:
        # TODO: handle type inference
        return VYPER_INT128

    def visit_NameConstant(self, node: ast.NameConstant, ctx: Context) -> VyperType:
        # TODO: handle None
        return VYPER_BOOL

    def visit_Attribute(self, node: ast.Attribute, ctx: Context) -> VyperType:
        return ctx.program.state[node.attr].type

    def visit_Subscript(self, node: ast.Subscript, ctx: Context) -> VyperType:
        return self.visit(node.value, ctx).value_type
    
    def visit_Name(self, node: ast.Name, ctx: Context) -> VyperType:
        arg = ctx.program.args.get(node.id)
        local = ctx.program.local_vars.get(node.id)
        return (arg or local).type