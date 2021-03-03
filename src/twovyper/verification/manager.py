"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from uuid import uuid1

from typing import Any, Dict, List, Optional

from twovyper.utils import unique

from twovyper.viper.jvmaccess import JVM
from twovyper.viper.typedefs import Node, AbstractSourcePosition
from twovyper.viper.typedefs import AbstractVerificationError
from twovyper.verification.error import Error, ErrorInfo
from twovyper.verification.rules import Rule

"""Error handling state is stored in singleton ``manager``."""


class ErrorManager:
    """A singleton object that stores the state needed for error handling."""

    def __init__(self) -> None:
        self._items: Dict[str, ErrorInfo] = {}
        self._conversion_rules: Dict[str, Rule] = {}

    def add_error_information(self, error_info: ErrorInfo, conversion_rules: Rule) -> str:
        """Add error information to state."""
        item_id = str(uuid1())
        assert item_id not in self._items
        self._items[item_id] = error_info
        if conversion_rules is not None:
            self._conversion_rules[item_id] = conversion_rules
        return item_id

    def clear(self) -> None:
        """Clear all state."""
        self._items.clear()
        self._conversion_rules.clear()

    def convert(
            self,
            errors: List[AbstractVerificationError],
            jvm: Optional[JVM]) -> List[Error]:
        """Convert Viper errors into 2vyper errors.

        It does that by wrapping in ``Error`` subclasses.
        """
        def eq(e1: Error, e2: Error) -> bool:
            ide = e1.string(True, False) == e2.string(True, False)
            normal = e1.string(False, False) == e2.string(False, False)
            return ide and normal

        return unique(eq, [self._convert_error(error, jvm) for error in errors])

    def get_vias(self, node_id: str) -> List[Any]:
        """Get via information for the given ``node_id``."""
        item = self._items[node_id]
        return item.vias

    def _get_error_info(self, pos: AbstractSourcePosition) -> Optional[ErrorInfo]:
        if hasattr(pos, 'id'):
            node_id = pos.id()
            return self._items[node_id]
        return None

    def _get_conversion_rules(
            self, position: AbstractSourcePosition) -> Optional[Rule]:
        if hasattr(position, 'id'):
            node_id = position.id()
            return self._conversion_rules.get(node_id)
        else:
            return None

    def _try_get_rules_workaround(
            self, node: Node, jvm: Optional[JVM]) -> Optional[Rule]:
        """Try to extract rules out of ``node``.

        Due to optimizations, Silicon sometimes returns not the correct
        offending node, but an And that contains it. This method tries
        to work around this problem.

        .. todo::

            In the long term we should discuss with Malte how to solve
            this problem properly.
        """
        rules = self._get_conversion_rules(node.pos())
        if rules or not jvm:
            return rules
        if (isinstance(node, jvm.viper.silver.ast.And) or
                isinstance(node, jvm.viper.silver.ast.Implies)):
            return (self._get_conversion_rules(node.left().pos()) or
                    self._get_conversion_rules(node.right().pos()) or
                    self._try_get_rules_workaround(node.left(), jvm) or
                    self._try_get_rules_workaround(node.right(), jvm))
        return

    def transformError(self, error: AbstractVerificationError) -> AbstractVerificationError:
        """ Transform silver error to a fixpoint. """
        old_error = None
        while old_error != error:
            old_error = error
            error = error.transformedError()
        return error

    def _convert_error(
            self, error: AbstractVerificationError,
            jvm: Optional[JVM]) -> Error:
        error = self.transformError(error)
        reason_pos = error.reason().offendingNode().pos()
        reason_item = self._get_error_info(reason_pos)
        position = error.pos()
        rules = self._try_get_rules_workaround(
            error.offendingNode(), jvm)
        if rules is None:
            rules = self._try_get_rules_workaround(
                error.reason().offendingNode(), jvm)
        if rules is None:
            rules = {}
        error_item = self._get_error_info(position)
        return Error(error, rules, reason_item, error_item, jvm)


manager = ErrorManager()
