"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

"""Wrappers for Scala error objects."""

import ast

from typing import Any, List

from nagini_translation.lib.errors.messages import ERRORS, REASONS, VAGUE_REASONS
from nagini_translation.lib.errors.rules import Rules


class Position:
    """Wrapper around ``AbstractSourcePosition``."""

    def __init__(self, position: 'ast.AbstractSourcePosition') -> None:
        self._position = position
        if hasattr(position, 'id'):
            self.node_id = position.id()
        else:
            self.node_id = None

    @property
    def file_name(self) -> str:
        """Return ``file``."""
        return self._position.file().toString()

    @property
    def line(self) -> int:
        """Return ``start.line``."""
        return self._position.line()

    @property
    def column(self) -> int:
        """Return ``start.column``."""
        return self._position.column()

    def __str__(self) -> str:
        return str(self._position)


class ErrorInfo:

    def __init__(self, function: str, node: ast.AST, vias, reason_string: str):
        self.function = function
        self.node = node
        self.vias = vias
        self.reason_string = reason_string 


class Reason:
    """Wrapper around ``AbstractErrorReason``."""

    def __init__(self, reason_id: str, reason: 'AbstractErrorReason', reason_info: ErrorInfo):
        self._reason = reason
        self.identifier = reason_id
        self._reason_info = reason_info
        self.offending_node = reason.offendingNode()
        self.position = Position(self.offending_node.pos())

    def __str__(self) -> str:
        return self.string(False)

    def string(self, show_viper_reason: bool) -> str:
        """
        Creates a string representation of this reason including a reference to the Python
        AST node that caused it.
        If no such node is available, either returns a partial message that describes the
        kind of error in general, or outputs the concrete Viper-level description of the
        error, depending on the parameter ``show_viper_reason``.
        """
        reason = self._reason_info.reason_string or self._reason_info.node
        if reason is None and self.identifier in VAGUE_REASONS:
            if not show_viper_reason:
                return VAGUE_REASONS[self.identifier]
            else:
                return self._reason.readableMessage()
        return REASONS[self.identifier](self._reason_info)


class Error:
    """Wrapper around ``AbstractVerificationError``."""

    def __init__(self, error: 'AbstractVerificationError', rules: Rules,
                 reason_item: ErrorInfo, error_item: ErrorInfo) -> None:

        # Translate error id.
        viper_reason = error.reason()
        error_id = error.id()
        reason_id = viper_reason.id()
        key = error_id, reason_id
        if key in rules:
            error_id, reason_id = rules[key]

        # Construct object.
        self._error = error
        self.identifier = error_id
        self._error_info = error_item
        if reason_item:
            self.reason = Reason(
                reason_id, viper_reason, reason_item)
        else:
            self.reason = Reason(reason_id, viper_reason)
        self.position = Position(error.pos())

    def pos(self) -> 'ast.AbstractSourcePosition':
        """Get position.

        .. todo:: Marco

            This method is only for compatibility with current testing
            infrastructure and should be removed.
        """
        return self._error.pos()

    @property
    def full_id(self) -> str:
        """Full error identifier."""
        return '{}:{}'.format(self.identifier, self.reason.identifier)

    @property
    def offending_node(self) -> 'ast.Node':
        """AST node where the error occurred."""
        return self._error.offendingNode()

    @property
    def readable_message(self) -> str:
        """Readable error message."""
        return self._error.readableMessage()

    @property
    def position_string(self) -> str:
        """Full error position as a string."""
        vias = self.reason._reason_info.vias or self._error_info.vias or []
        vias_string = ''.join(
            ', via {0} at {1}'.format(reason, pos)
            for reason, pos in vias)
        return '{}{}'.format(self.position, vias_string)

    @property
    def message(self) -> str:
        """Human readable error message."""
        if self._error_info:
            return ERRORS[self.identifier](self._error_info)
        # If we don't have a node, fall back to the original Silver message,
        # it's better than nothing.
        return self._error.text()

    def __str__(self) -> str:
        return self.string(False, False)

    def string(self, ide_mode: bool, show_viper_errors: bool) -> str:
        """
        Format error.

        Creates an appropriate error message (referring to the
        responsible Python code) for the given Viper error.

        The error format is either optimized for human readability or uses the same format
        as IDE-mode Viper error messages, depending on the first parameter.
        The second parameter determines if the message may show Viper-level error
        explanations if no Python-level explanation is available.
        """
        if ide_mode:
            return '{0}:{1}:{2}: error: {3} {4}'.format(
                self.position.file_name,
                self.position.line, self.position.column, self.message,
                self.reason)
        else:
            return '{0} {1} ({2})'.format(
                self.message, self.reason.string(show_viper_errors), self.position_string)
