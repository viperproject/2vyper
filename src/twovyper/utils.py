"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import contextmanager
from itertools import chain
from typing import Callable, Iterable, List, Optional, TypeVar

from twovyper.ast import ast_nodes as ast


_ = object()


@contextmanager
def switch(*values):
    def match(*v, where=True):
        if not where or len(values) != len(v):
            return False

        return all(case is _ or actual == case for actual, case in zip(values, v))

    yield match


T = TypeVar('T')


def first(iterable: Iterable[T]) -> Optional[T]:
    return next(iter(iterable), None)


def first_index(statisfying: Callable[[T], bool], l) -> int:
    return next((i for i, v in enumerate(l) if statisfying(v)), -1)


def flatten(iterables: Iterable[Iterable[T]]) -> List[T]:
    return [item for subiterable in iterables for item in subiterable]


def unique(eq, iterable: Iterable[T]) -> List[T]:
    unique_iterable: List[T] = []
    for elem in iterable:
        for uelem in unique_iterable:
            if eq(elem, uelem):
                break
        else:
            unique_iterable.append(elem)

    return unique_iterable


class DicitionaryView:

    def __init__(self, dicts):
        self.dicts = dicts

    def __getitem__(self, key):
        for d in self.dicts:
            opt_value = d.get(key)
            if opt_value is not None:
                return opt_value
        else:
            raise KeyError(f"{key} not present in dict")


def seq_to_list(scala_iterable):
    lst = []
    it = scala_iterable.iterator()
    while it.hasNext():
        lst.append(it.next())
    return lst


def list_to_seq(lst, jvm):
    seq = jvm.scala.collection.mutable.ArraySeq(len(lst))
    for i, element in enumerate(lst):
        seq.update(i, element)
    return seq


class Subscriptable(type):
    """
    A metaclass to add dictionary lookup functionality to a class.
    The class needs to implement the `_subscript(_)` method.
    """

    def __getitem__(cls, val):
        return cls._subscript(val)


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


# TODO: move to ast package
def pprint(node: ast.Node, preserve_newlines: bool = False) -> str:
    with open(node.file, 'r') as file:
        source = file.read()

    lines = _split_lines(source)

    lineno = node.lineno - 1
    end_lineno = node.end_lineno - 1
    col_offset = node.col_offset - 1
    end_col_offset = node.end_col_offset - 1

    if end_lineno == lineno:
        res = lines[lineno].encode()[col_offset:end_col_offset].decode()
    else:
        first = lines[lineno].encode()[col_offset:].decode()
        middle = lines[lineno + 1:end_lineno]
        last = lines[min(end_lineno, len(lines) - 1)].encode()[:end_col_offset].decode()
        sep = '\n' if preserve_newlines else ' '
        res = sep.join(chain([first], middle, [last]))

    return res if preserve_newlines else f'({res})'
