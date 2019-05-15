"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import List

from nagini_translation.lib.viper_ast import ViperAST
from nagini_translation.lib.errors import error_manager, Rules
from nagini_translation.lib.errors.wrappers import ErrorInfo

from nagini_translation.translation.context import Context


class PositionTranslator:

    def __init__(self, viper_ast: ViperAST):
        self.viper_ast = viper_ast

    def _register_potential_error(self, node, ctx: Context, rules: Rules = None, vias = [], error_string: str = None) -> str:
        name = None if not ctx.function else ctx.function.name
        error_info = ErrorInfo(name, node, vias, error_string)
        id = error_manager.add_error_information(error_info, rules)
        return id

    def to_position(self,
                    node: ast.AST,
                    ctx: Context,
                    rules: Rules = None,
                    vias = [],
                    error_string: str = None) -> 'silver.ast.Position':
        """
        Extracts the position from a node, assigns an ID to the node and stores
        the node and the position in the context for it.
        """
        id = self._register_potential_error(node, ctx, rules, vias, error_string)
        return self.viper_ast.to_position(node, id, ctx.file)

    def no_position(self, error_string: str = None) -> 'silver.ast.Position':
        return self.viper_ast.NoPosition

    def to_info(self, comments: List[str]) -> 'silver.ast.Info':
        """
        Wraps the given comments into an Info object.
        If ctx.info is set to override the given info, returns that.
        """
        if comments:
            return self.viper_ast.SimpleInfo(comments)
        else:
            return self.viper_ast.NoInfo

    def no_info(self) -> 'silver.ast.Info':
        return self.to_info([])


class CommonTranslator:

    def fail_if(self, cond, ctx: Context, pos = None):
        body = [self.viper_ast.Goto(ctx.revert_label, pos)]
        block = self.viper_ast.Seqn(body, pos)
        empty = self.viper_ast.Seqn([], pos)
        return self.viper_ast.If(cond, block, empty, pos)


class NodeTranslator(PositionTranslator, CommonTranslator):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast)

    def translate(self, node, ctx):
        """Translate a node."""
        method = 'translate_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_translate)
        return visitor(node, ctx)

    def generic_translate(self, node, ctx):
        raise AssertionError(f"Node of type {type(node)} not supported.")
