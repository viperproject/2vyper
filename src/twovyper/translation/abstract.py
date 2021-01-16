"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Any, Dict, List, Iterable

from twovyper.ast import ast_nodes as ast
from twovyper.ast.visitors import NodeVisitor

from twovyper.translation.context import Context

from twovyper.verification import error_manager
from twovyper.verification.error import ErrorInfo, ModelTransformation, Via
from twovyper.verification.rules import Rule

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr, Stmt
from twovyper.viper.typedefs import Position, Info


class CommonTranslator:

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

    def _register_potential_error(self,
                                  node,
                                  ctx: Context,
                                  rules: Rule = None,
                                  vias: List[Via] = [],
                                  modelt: ModelTransformation = None,
                                  values: Dict[str, Any] = {}) -> str:
        # Inline vias are in reverse order, as the outermost is first,
        # and successive vias are appended. For the error output, changing
        # the order makes more sense.
        inline_vias = list(reversed(ctx.inline_vias))
        values = {'function': ctx.function, **values}
        error_info = ErrorInfo(node, inline_vias + vias, modelt, values)
        id = error_manager.add_error_information(error_info, rules)
        return id

    def to_position(self,
                    node: ast.Node,
                    ctx: Context,
                    rules: Rule = None,
                    vias: List[Via] = [],
                    modelt: ModelTransformation = None,
                    values: Dict[str, Any] = {}) -> Position:
        """
        Extracts the position from a node, assigns an ID to the node and stores
        the node and the position in the context for it.
        """
        id = self._register_potential_error(node, ctx, rules, vias, modelt, values)
        return self.viper_ast.to_position(node, id)

    def no_position(self) -> Position:
        return self.viper_ast.NoPosition

    def to_info(self, comments: List[str]) -> Info:
        """
        Wraps the given comments into an Info object.
        """
        if comments:
            return self.viper_ast.SimpleInfo(comments)
        else:
            return self.viper_ast.NoInfo

    def no_info(self) -> Info:
        return self.to_info([])

    def fail_if(self, cond: Expr, stmts: List[Stmt], res: List[Stmt], ctx: Context, pos=None, info=None):
        body = [*stmts, self.viper_ast.Goto(ctx.revert_label, pos)]
        res.append(self.viper_ast.If(cond, body, [], pos, info))

    def seqn_with_info(self, stmts: [Stmt], comment: str, res: List[Stmt]):
        if stmts:
            info = self.to_info([comment])
            res.append(self.viper_ast.Seqn(stmts, info=info))


class NodeTranslator(NodeVisitor, CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

    @property
    def method_name(self) -> str:
        return 'translate'

    def translate(self, node: ast.Node, res: List[Stmt], ctx: Context):
        return self.visit(node, res, ctx)

    def visit_nodes(self, nodes: Iterable[ast.Node], *args):
        ret = []
        for node in nodes:
            ret += self.visit(node, *args)
        return ret

    def generic_visit(self, node: ast.Node, *args):
        raise AssertionError(f"Node of type {type(node)} not supported.")
