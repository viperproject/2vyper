"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Optional, Tuple

from twovyper.ast import ast_nodes as ast, names

from twovyper.translation import helpers, mangled
from twovyper.translation.abstract import NodeTranslator
from twovyper.translation.context import Context

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt, StmtsAndExpr


class ResourceTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

    @property
    def specification_translator(self):
        from twovyper.translation.specification import SpecificationTranslator
        return SpecificationTranslator(self.viper_ast)

    def resource(self, name: str, args: List[Expr], ctx: Context, pos=None) -> Expr:
        resource_type = ctx.program.resources[name].type
        return helpers.struct_init(self.viper_ast, args, resource_type, pos)

    def creator_resource(self, name: str, resource: Expr, ctx: Context, pos=None) -> Expr:
        creator_name = mangled.creator_resource_name(name)
        creator_resource_type = ctx.program.resources[creator_name].type
        return helpers.struct_init(self.viper_ast, [resource], creator_resource_type, pos)

    def translate(self, resource: Optional[ast.Node], ctx: Context) -> StmtsAndExpr:
        if resource:
            return super().translate(resource, ctx)
        else:
            return [], self.resource(names.WEI, [], ctx)

    def translate_exchange(self, exchange: Optional[ast.Exchange], ctx: Context) -> Tuple[Stmt, Expr, Expr]:
        if not exchange:
            wei_resource = self.resource(names.WEI, [], ctx)
            return [], wei_resource, wei_resource

        stmts1, r1 = self.translate(exchange.value1, ctx)
        stmts2, r2 = self.translate(exchange.value2, ctx)
        return stmts1 + stmts2, r1, r2

    def translate_Name(self, node: ast.Name, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)
        return [], self.resource(node.id, [], ctx, pos)

    def translate_FunctionCall(self, node: ast.FunctionCall, ctx: Context) -> StmtsAndExpr:
        pos = self.to_position(node, ctx)
        if node.name == names.CREATOR:
            resource_stmts, resource = self.translate(node.args[0], ctx)
            return resource_stmts, self.creator_resource(node.args[0].type.name, resource, ctx, pos)
        else:
            args_stmts, args = self.collect(self.specification_translator.translate(arg, ctx) for arg in node.args)
            return args_stmts, self.resource(node.name, args, ctx, pos)
