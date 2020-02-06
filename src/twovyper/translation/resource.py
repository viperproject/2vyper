"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Optional, Tuple

from twovyper.ast import ast_nodes as ast, names

from twovyper.translation import helpers
from twovyper.translation.abstract import NodeTranslator
from twovyper.translation.context import Context

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


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

    def creator_resource(self, resource: Expr, ctx: Context, pos=None) -> Expr:
        creator_resource_type = helpers.creator_resource().type
        return helpers.struct_init(self.viper_ast, [resource], creator_resource_type, pos)

    def translate(self, resource: Optional[ast.Node], res: List[Stmt], ctx: Context) -> Expr:
        if resource:
            return super().translate(resource, res, ctx)
        else:
            return self.resource(names.WEI, [], ctx)

    def translate_exchange(self, exchange: Optional[ast.Exchange], res: Stmt, ctx: Context) -> Tuple[Expr, Expr]:
        if not exchange:
            wei_resource = self.resource(names.WEI, [], ctx)
            return wei_resource, wei_resource

        left = self.translate(exchange.left, res, ctx)
        right = self.translate(exchange.right, res, ctx)
        return left, right

    def translate_Name(self, node: ast.Name, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        return self.resource(node.id, [], ctx, pos)

    def translate_FunctionCall(self, node: ast.FunctionCall, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        if node.name == names.CREATOR:
            resource = self.translate(node.args[0], res, ctx)
            return self.creator_resource(resource, ctx, pos)
        else:
            args = [self.specification_translator.translate(arg, res, ctx) for arg in node.args]
            return self.resource(node.name, args, ctx, pos)
