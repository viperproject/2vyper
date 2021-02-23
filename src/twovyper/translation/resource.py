"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from functools import reduce
from typing import List, Optional, Tuple, Union

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.nodes import Resource

from twovyper.translation import helpers
from twovyper.translation.abstract import NodeTranslator
from twovyper.translation.context import Context

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt


class ResourceTranslator(NodeTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

    @property
    def specification_translator(self):
        from twovyper.translation.specification import SpecificationTranslator
        return SpecificationTranslator(self.viper_ast)

    def underlying_wei_resource(self, ctx, pos=None) -> Expr:
        _, expr = self._resource(names.UNDERLYING_WEI, [], ctx, pos)
        return expr

    def resource(self, name: str, args: List[Expr], ctx: Context, pos=None) -> Expr:
        self_address = ctx.self_address or helpers.self_address(self.viper_ast)
        args = list(args)
        args.append(self_address)
        _, expr = self._resource(name, args, ctx, pos)
        return expr

    def _resource(self, name: str, args: List[Expr], ctx: Context, pos=None) -> Tuple[Resource, Expr]:
        resources = ctx.program.resources.get(name)
        assert resources is not None and len(resources) > 0
        resource = ctx.current_program.own_resources.get(name, resources[0])
        return resource, helpers.struct_init(self.viper_ast, args, resource.type, pos)

    def creator_resource(self, resource: Expr, _: Context, pos=None) -> Expr:
        creator_resource_type = helpers.creator_resource().type
        return helpers.struct_init(self.viper_ast, [resource], creator_resource_type, pos)

    def translate(self, resource: Optional[ast.Node], res: List[Stmt], ctx: Context,
                  return_resource=False) -> Union[Expr, Tuple[Resource, Expr]]:
        if resource:
            resource, expr = super().translate(resource, res, ctx)
        else:
            self_address = ctx.self_address or helpers.self_address(self.viper_ast)
            resource, expr = self._resource(names.WEI, [self_address], ctx)

        if return_resource:
            return resource, expr
        else:
            return expr

    def translate_resources_for_quantified_expr(self, resources: List[Tuple[str, Resource]], ctx: Context, pos=None,
                                                translate_underlying=False, args_idx_start=0):
        counter = args_idx_start
        translated_resource_with_args_and_type_assumption = []
        for name, resource in resources:
            type_assumptions = []
            args = []
            for idx, arg_type in enumerate(resource.type.member_types.values()):
                viper_type = self.specification_translator.type_translator.translate(arg_type, ctx)
                arg = self.viper_ast.LocalVarDecl(f'$arg{idx}${counter}', viper_type, pos)
                counter += 1
                args.append(arg)
                arg_var = arg.localVar()
                type_assumptions.extend(self.specification_translator.type_translator
                                        .type_assumptions(arg_var, arg_type, ctx))
            type_cond = reduce(lambda l, r: self.viper_ast.And(l, r, pos), type_assumptions, self.viper_ast.TrueLit())
            if translate_underlying:
                assert isinstance(resource.type, types.DerivedResourceType)
                if resource.name == names.WEI:
                    t_resource = self.underlying_wei_resource(ctx)
                else:
                    stmts = []
                    underlying_address = self.specification_translator.translate(
                        resource.underlying_address, stmts, ctx)
                    assert not stmts
                    t_resource = helpers.struct_init(
                        self.viper_ast, [arg.localVar() for arg in args] + [underlying_address],
                        resource.type.underlying_resource, pos)
            else:
                t_resource = self.resource(name, [arg.localVar() for arg in args], ctx)
            translated_resource_with_args_and_type_assumption.append((t_resource, args, type_cond))
        return translated_resource_with_args_and_type_assumption

    def translate_with_underlying(self, top_node: Optional[ast.FunctionCall], res: List[Stmt], ctx: Context,
                                  return_resource=False) -> Union[Tuple[Expr, Expr], Tuple[Resource, Expr, Expr]]:
        if top_node:
            resource_node = top_node.resource
            underlying_resource_node = top_node.underlying_resource
            resource, expr = self.translate(resource_node, res, ctx, True)
            underlying_resource_expr = self.translate(underlying_resource_node, res, ctx)
        else:
            resource, expr = self.translate(None, res, ctx, True)
            underlying_resource_expr = self.underlying_wei_resource(ctx)

        if return_resource:
            return resource, expr, underlying_resource_expr
        else:
            return expr, underlying_resource_expr

    def translate_exchange(self, exchange: Optional[ast.Exchange], res: Stmt, ctx: Context,
                           return_resource=False) -> Tuple[Union[Expr, Tuple[Resource, Expr]],
                                                           Union[Expr, Tuple[Resource, Expr]]]:
        if not exchange:
            wei_resource = self.translate(None, res, ctx, return_resource)
            return wei_resource, wei_resource

        left = self.translate(exchange.left, res, ctx, return_resource)
        right = self.translate(exchange.right, res, ctx, return_resource)
        return left, right

    def translate_Name(self, node: ast.Name, _: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        if node.id == names.UNDERLYING_WEI:
            return self._resource(node.id, [], ctx, pos)
        else:
            self_address = ctx.self_address or helpers.self_address(self.viper_ast)
            return self._resource(node.id, [self_address], ctx, pos)

    def translate_FunctionCall(self, node: ast.FunctionCall, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        if node.name == names.CREATOR:
            resource = self.translate(node.args[0], res, ctx)
            return None, self.creator_resource(resource, ctx, pos)
        elif node.resource:
            address = self.specification_translator.translate(node.resource, res, ctx)
        else:
            address = ctx.self_address or helpers.self_address(self.viper_ast)
        args = [self.specification_translator.translate(arg, res, ctx) for arg in node.args]
        args.append(address)
        return self._resource(node.name, args, ctx, pos)

    def translate_Attribute(self, node: ast.Attribute, _: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        assert isinstance(node.value, ast.Name)
        interface = ctx.current_program.interfaces[node.value.id]
        with ctx.program_scope(interface):
            self_address = ctx.self_address or helpers.self_address(self.viper_ast)
            return self._resource(node.attr, [self_address], ctx, pos)

    def translate_ReceiverCall(self, node: ast.ReceiverCall, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        if isinstance(node.receiver, ast.Name):
            interface = ctx.current_program.interfaces[node.receiver.id]
            address = ctx.self_address or helpers.self_address(self.viper_ast)
        elif isinstance(node.receiver, ast.Subscript):
            assert isinstance(node.receiver.value, ast.Attribute)
            assert isinstance(node.receiver.value.value, ast.Name)
            interface_name = node.receiver.value.value.id
            interface = ctx.current_program.interfaces[interface_name]
            address = self.specification_translator.translate(node.receiver.index, res, ctx)
        else:
            assert False

        with ctx.program_scope(interface):
            args = [self.specification_translator.translate(arg, res, ctx) for arg in node.args]
            args.append(address)
            return self._resource(node.name, args, ctx, pos)

    def translate_Subscript(self, node: ast.Subscript, res: List[Stmt], ctx: Context) -> Expr:
        pos = self.to_position(node, ctx)
        other_address = self.specification_translator.translate(node.index, res, ctx)
        if isinstance(node.value, ast.Attribute):
            assert isinstance(node.value.value, ast.Name)
            interface = ctx.current_program.interfaces[node.value.value.id]
            with ctx.program_scope(interface):
                return self._resource(node.value.attr, [other_address], ctx, pos)
        elif isinstance(node.value, ast.Name):
            return self._resource(node.value.id, [other_address], ctx, pos)
        else:
            assert False
