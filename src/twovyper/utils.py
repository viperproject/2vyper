"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import contextmanager
from typing import Callable, Iterable, List, Optional, TypeVar


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
