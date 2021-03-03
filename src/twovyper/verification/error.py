"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Any, Dict, List, Optional

from twovyper.ast import ast_nodes as ast

from twovyper.viper.typedefs import Node, AbstractSourcePosition
from twovyper.viper.typedefs import AbstractVerificationError, AbstractErrorReason

from twovyper.verification.messages import ERRORS, REASONS
from twovyper.verification.model import Model, ModelTransformation
from twovyper.verification.rules import Rule


"""Wrappers for Scala error objects."""


class Position:
    """Wrapper around ``AbstractSourcePosition``."""

    def __init__(self, position: AbstractSourcePosition):
        self._position = position
        if hasattr(position, 'id'):
            self.node_id = position.id()
        else:
            self.node_id = None

    @property
    def file_name(self) -> str:
        """Return ``file``."""
        return str(self._position.file())

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


class Via:

    def __init__(self, origin: str, position: AbstractSourcePosition):
        self.origin = origin
        self.position = position


class ErrorInfo:

    def __init__(self,
                 node: ast.Node,
                 vias: List[Via],
                 model_transformation: Optional[ModelTransformation],
                 values: Dict[str, Any]):
        self.node = node
        self.vias = vias
        self.model_transformation = model_transformation
        self.values = values

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            try:
                return self.values.get(name)
            except KeyError:
                raise AttributeError(f"'ErrorInfo' object has no attribute '{name}'")


class Reason:
    """Wrapper around ``AbstractErrorReason``."""

    def __init__(self, reason_id: str, reason: AbstractErrorReason, reason_info: ErrorInfo):
        self._reason = reason
        self.identifier = reason_id
        self._reason_info = reason_info
        self.offending_node = reason.offendingNode()
        self.position = Position(self.offending_node.pos())

    def __str__(self) -> str:
        """
        Creates a string representation of this reason including a reference to the Python
        AST node that caused it.
        """
        return REASONS[self.identifier](self._reason_info)


class Error:
    """Wrapper around ``AbstractVerificationError``."""

    def __init__(self, error: AbstractVerificationError, rules: Rule,
                 reason_item: ErrorInfo, error_item: ErrorInfo, jvm) -> None:

        # Translate error id.
        viper_reason = error.reason()
        error_id = error.id()
        reason_id = viper_reason.id()

        # This error might come from a precondition fail of the Viper function "$pure$return_get" which has no position.
        # if the reason_item could not be found due to this, use the error_item instead.
        if error_id == 'application.precondition' and reason_item is None:
            reason_item = error_item

        key = error_id, reason_id
        if key in rules:
            error_id, reason_id = rules[key]

        # Construct object.
        self._error = error
        self.identifier = error_id
        self._error_info = error_item
        self.reason = Reason(reason_id, viper_reason, reason_item)
        if error.counterexample().isDefined():
            self.model = Model(error, jvm, error_item.model_transformation)
        else:
            self._model = None
        self.position = Position(error.pos())

    def pos(self) -> AbstractSourcePosition:
        """
        Get position.
        """
        return self._error.pos()

    @property
    def full_id(self) -> str:
        """
        Full error identifier.
        """
        return f"{self.identifier}:{self.reason.identifier}"

    @property
    def offending_node(self) -> Node:
        """
        AST node where the error occurred.
        """
        return self._error.offendingNode()

    @property
    def readable_message(self) -> str:
        """
        Readable error message.
        """
        return self._error.readableMessage()

    @property
    def position_string(self) -> str:
        """
        Full error position as a string.
        """
        vias = self._error_info.vias or self.reason._reason_info.vias or []
        vias_string = "".join(f", via {via.origin} at {via.position}" for via in vias)
        return f"{self.position}{vias_string}"

    @property
    def message(self) -> str:
        """
        Human readable error message.
        """
        return ERRORS[self.identifier](self._error_info)

    def __str__(self) -> str:
        return self.string(False, False)

    def string(self, ide_mode: bool, include_model: bool = False) -> str:
        """
        Format error.

        Creates an appropriate error message (referring to the
        responsible Python code) for the given Viper error.

        The error format is either optimized for human readability or uses the same format
        as IDE-mode Viper error messages, depending on the first parameter.
        The second parameter determines if the message may show Viper-level error
        explanations if no Python-level explanation is available.
        """
        assert not (ide_mode and include_model)

        if ide_mode:
            file_name = self.position.file_name
            line = self.position.line
            col = self.position.column
            msg = self.message
            reason = self.reason
            return f"{file_name}:{line}:{col}: error: {msg} {reason}"
        else:
            msg = self.message
            reason = self.reason
            pos = self.position_string
            error_msg = f"{msg} {reason} ({pos})"
            if include_model and self.model:
                return f"{error_msg}\nCounterexample:\n{self.model}"
            else:
                return error_msg
