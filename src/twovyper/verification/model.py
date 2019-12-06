"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging

from typing import Callable, Dict, Optional, Tuple

from twovyper.utils import seq_to_list

from twovyper.viper.typedefs import AbstractVerificationError


ModelTransformation = Callable[[str, str], Tuple[str, str]]


class Model:

    def __init__(self, error: AbstractVerificationError, transform: Optional[ModelTransformation]):
        self._model = error.parsedModel().get()
        self._transform = transform
        self.values()

    def values(self) -> Dict[str, str]:
        res = {}
        if self._model and self._transform:
            entries = self._model.entries()
            for name_entry in seq_to_list(entries):
                name = str(name_entry._1())
                value = str(name_entry._2())

                logging.debug(f"Parsing '{name}': {value}")

                py_value = _eval_value(_parse_value(value))
                transformation = self._transform(name, py_value)
                if transformation:
                    name, value = transformation
                    res[name] = value

        return res

    def __str__(self):
        return "\n".join(f"   {name} = {value}" for name, value in sorted(self.values().items()))


def _parse_value(val: str):
    """
    Parses a model expression to a list of strings expressions.
    Example: (- (- 12)) --> [[-, [-, 12]]]
    """
    it = iter(val)

    def parse(it):
        args = []
        current_word = ''

        def new_word():
            nonlocal current_word
            if current_word:
                args.append(current_word)
                current_word = ''

        while True:
            c = next(it, None)
            if c is None or c == ')':
                new_word()
                return args
            elif c == '(':
                new_word()
                func = parse(it)
                args.append(func)
            elif c.isspace():
                new_word()
            else:
                current_word += c

    return parse(it)


def _eval_func(val):
    if isinstance(val, str):
        if val == '+':
            return lambda n: n
        elif val == '-':
            return lambda n: -n
    elif isinstance(val, list):
        assert len(val) == 1
        return _eval_func(val[0])


def _eval_value(val):
    """
    Evaluates a previously parsed expression. Suported are:
       - Constants: true, false, 0, 1, ...
       - Names: $succ, ...
       - Unary operations: +, -
    """
    if isinstance(val, str):
        if val == 'true':
            return True
        elif val == 'false':
            return False
        try:
            return int(val)
        except ValueError:
            return val
    elif isinstance(val, list) and len(val) == 1:
        return _eval_value(val[0])
    elif isinstance(val, list):
        func = _eval_func(val[0])
        args = [_eval_value(v) for v in val[1:]]
        return func(*args)
    else:
        assert False
