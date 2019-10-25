"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import abc
import ast
import astunparse

from typing import Iterable
from contextlib import contextmanager


_ = object()


@contextmanager
def switch(*values):
    def match(*v, where=True):
        if not where or len(values) != len(v):
            return False

        return all(case is _ or actual == case for actual, case in zip(values, v))

    yield match


def first(iterable: Iterable):
    return next(iter(iterable), None)


def first_index(statisfying, l):
    return next((i for i, v in enumerate(l) if statisfying(v)), -1)


def flatten(iterables: Iterable[Iterable]):
    return [item for subiterable in iterables for item in subiterable]


def unique(eq, iterable: Iterable):
    unique_iterable = []
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


def pprint(node: ast.AST) -> str:
    res = astunparse.unparse(node)
    res = res.replace('\n', '')
    return res


class NodeVisitor(abc.ABC):

    @abc.abstractproperty
    def method_name(self) -> str:
        return None

    def visit(self, node, *args):
        method = f'{self.method_name}_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args)

    def generic_visit(self, node, *args):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item, *args)
            elif isinstance(value, ast.AST):
                self.visit(value, *args)
        return None
