"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast
import astunparse


class InvalidVyperException(Exception):

    def __init__(self, vyper_output: str):
        self.message = f"Not a valid Vyper contract:\n{vyper_output}"
        super().__init__(self.message)


class TranslationException(Exception):

    def __init__(self, node: ast.AST, message: str):
        super().__init__(message)
        self.message = message
        self.node = node

    def error_string(self, file: str) -> str:
        line = str(self.node.lineno)
        col = str(self.node.col_offset)
        return f"{self.message} ({file}@{line}.{col})"


class UnsupportedException(TranslationException):
    """
    Exception that is thrown when attempting to translate a Vyper element not
    currently supported
    """

    def __init__(self, node: ast.AST, message: str = None):
        self.node = node
        if not message:
            message = astunparse.unparse(node)
        super().__init__(node, f"Not supported: {message}")


class InvalidProgramException(TranslationException):
    """
    Signals that the input program is invalid and cannot be translated
    """

    def __init__(self, node: ast.AST, reason_code: str, message: str = None):
        self.node = node
        self.code = 'invalid.program'
        self.reason_code = reason_code
        if not message:
            node_msg = astunparse.unparse(node)
            message = f"Node {node_msg} not allowed here."
        super().__init__(node, f"Invalid program: {message}")


class ConsistencyException(Exception):
    """
    Exception reporting that the translated AST has a consistency error
    """

    def __init__(self, message: str, errors) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors
