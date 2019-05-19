"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast
import astunparse


def first_index(statisfying, l):
    return next(i for i, v in enumerate(l) if statisfying(v))


def flatten(lists):
    return [item for sublist in lists for item in sublist]


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
