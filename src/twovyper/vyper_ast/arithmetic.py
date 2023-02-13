"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from twovyper.utils import Subscriptable


def sign(a: int) -> int:
    if a > 0:
        return 1
    elif a < 0:
        return -1
    else:
        return 0


def div(a: int, b: int) -> int:
    """
    Truncating division of two integers.
    """
    return sign(a) * sign(b) * (abs(a) // abs(b))


def mod(a: int, b: int) -> int:
    """
    Truncating modulo of two integers.
    """
    return sign(a) * (abs(a) % abs(b))


class Decimal(object, metaclass=Subscriptable):

    def __init__(self):
        assert False

    _cache = {}

    def _subscript(number_of_digits: int):
        # This is the function that gets called when using dictionary lookup syntax.
        # For example, Decimal[10] returns a class of decimals with 10 digits. The class
        # is cached so that Decimal[10] always returns the same class, which means that
        # type(Decimal[10](1)) == type(Decimal[10](2)).

        cached_class = Decimal._cache.get(number_of_digits)
        if cached_class:
            return cached_class

        class _Decimal(Decimal):

            def __init__(self, value: int = None, scaled_value: int = None):
                assert (value is None) != (scaled_value is None)

                self.number_of_digits = number_of_digits
                self.scaling_factor = 10 ** number_of_digits
                self.scaled_value = scaled_value if value is None else value * self.scaling_factor

            def __eq__(self, other):
                if isinstance(other, _Decimal):
                    return self.scaled_value == other.scaled_value
                else:
                    return False

            def __hash__(self):
                return hash(self.scaled_value)

            def __str__(self):
                dv = div(self.scaled_value, self.scaling_factor)
                md = mod(self.scaled_value, self.scaling_factor)
                return f'{dv}.{str(md).zfill(self.number_of_digits)}'

        Decimal._cache[number_of_digits] = _Decimal
        return _Decimal
