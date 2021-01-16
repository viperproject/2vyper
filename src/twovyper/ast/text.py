"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from itertools import chain

from twovyper.ast import ast_nodes as ast


def _split_lines(source):
    idx = 0
    lines = []
    next_line = ''
    while idx < len(source):
        c = source[idx]
        idx += 1
        if c == '\r' and idx < len(source) and source[idx] == '\n':
            idx += 1
        if c in '\r\n':
            lines.append(next_line)
            next_line = ''
        else:
            next_line += c

    if next_line:
        lines.append(next_line)
    return lines


def pprint(node: ast.Node, preserve_newlines: bool = False) -> str:
    with open(node.file, 'r') as file:
        source = file.read()

    lines = _split_lines(source)

    lineno = node.lineno - 1
    end_lineno = node.end_lineno - 1
    col_offset = node.col_offset - 1
    end_col_offset = node.end_col_offset - 1

    if end_lineno == lineno:
        text = lines[lineno].encode()[col_offset:end_col_offset].decode()
    else:
        first = lines[lineno].encode()[col_offset:].decode()
        middle = lines[lineno + 1:end_lineno]
        last = lines[min(end_lineno, len(lines) - 1)].encode()[:end_col_offset].decode()
        sep = '\n' if preserve_newlines else ' '
        text = sep.join(chain([first], middle, [last]))

    stripped = text.strip()
    return stripped if preserve_newlines else f'({stripped})'
