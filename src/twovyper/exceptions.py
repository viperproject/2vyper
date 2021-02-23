"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os

from twovyper.ast import ast_nodes as ast
from twovyper.ast.text import pprint


class TwoVyperException(Exception):

    def __init__(self, message: str):
        self.message = message


class InvalidVyperException(TwoVyperException):
    """
    Exception indicating that the file is not a valid Vyper contract.
    """

    def __init__(self, vyper_output: str):
        message = f"Not a valid Vyper contract:\n{vyper_output}"
        super().__init__(message)


class ParseException(TwoVyperException):
    """
    Exception that is thrown if the contract cannot be parsed.
    """

    def __init__(self, message: str):
        super().__init__(message)


class TranslationException(TwoVyperException):

    def __init__(self, node: ast.Node, message: str):
        super().__init__(message)
        self.node = node

    def error_string(self) -> str:
        file_name = os.path.basename(self.node.file)
        line = self.node.lineno
        col = self.node.col_offset
        return f"{self.message} ({file_name}@{line}.{col})"


class UnsupportedException(TranslationException):
    """
    Exception that is thrown when attempting to translate a Vyper element not
    currently supported.
    """

    def __init__(self, node: ast.Node, message: str = None):
        self.node = node
        if not message:
            message = pprint(node)
        super().__init__(node, f"Not supported: {message}")


class InvalidProgramException(TranslationException):
    """
    Signals that the input program is invalid and cannot be translated.
    """

    def __init__(self, node: ast.Node, reason_code: str, message: str = None):
        self.node = node
        self.code = 'invalid.program'
        self.reason_code = reason_code
        if not message:
            node_msg = pprint(node, True)
            message = f"Node\n{node_msg}\nnot allowed here."
        super().__init__(node, f"Invalid program ({self.reason_code}): {message}")


class ConsistencyException(TwoVyperException):
    """
    Exception reporting that the translated AST has a consistency error.
    """

    def __init__(self, program, message: str, errors):
        super().__init__(message)
        self.program = program
        self.errors = errors


class UnsupportedVersionException(TwoVyperException):
    """
    Exception that is thrown when a unsupported Vyper version is used by a contract.
    """

    def __init__(self, message: str = None):
        if message is None:
            from twovyper.vyper import get_vyper_version
            message = f"The Vyper version ({get_vyper_version()}) used by the contract is not supported."
        super().__init__(message)
