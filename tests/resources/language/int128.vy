#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: implies(success() and a == 4 and b == 2, result() == 6)
#@ ensures: implies(success() and a == -4 and b == 2, result() == -2)
#@ ensures: implies(success() and a == -4 and b == -2, result() == -6)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success() and a == -4 and b == -2, result() == 6)
@public
def _add(a: int128, b: int128) -> int128:
    return a + b


#@ ensures: implies(success() and a == 4 and b == 2, result() == 2)
#@ ensures: implies(success() and a == -4 and b == 2, result() == -6)
#@ ensures: implies(success() and a == -4 and b == -2, result() == -2)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success() and a == -4 and b == -2, result() == 2)
@public
def _sub(a: int128, b: int128) -> int128:
    return a - b


#@ ensures: implies(success() and a == 4 and b == 2, result() == 8)
#@ ensures: implies(success() and a == -4 and b == 2, result() == -8)
#@ ensures: implies(success() and a == -4 and b == -2, result() == 8)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success() and a == -4 and b == -2, result() == -8)
@public
def _mul(a: int128, b: int128) -> int128:
    return a * b


#@ ensures: implies(success() and a == 4 and b == 2, result() == 2)
#@ ensures: implies(success() and a == -4 and b == 2, result() == -2)
#@ ensures: implies(success() and a == -4 and b == -2, result() == 2)
#@ ensures: implies(success() and a == 4 and b == 3, result() == 1)
#@ ensures: implies(success() and a == -4 and b == 3, result() == -1)
#@ ensures: implies(success() and a == -4 and b == -3, result() == 1)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success() and a == -4 and b == -2, result() == -2)
@public
def _div(a: int128, b: int128) -> int128:
    return a / b


#@ ensures: implies(success() and a == 4 and b == 2, result() == 0)
#@ ensures: implies(success() and a == -4 and b == 2, result() == 0)
#@ ensures: implies(success() and a == -4 and b == -2, result() == 0)
#@ ensures: implies(success() and a == 4 and b == 3, result() == 1)
#@ ensures: implies(success() and a == -4 and b == 3, result() == -1)
#@ ensures: implies(success() and a == -4 and b == -3, result() == -1)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success() and a == -4 and b == -2, result() == -2)
@public
def _mod(a: int128, b: int128) -> int128:
    return a % b


#@ ensures: forall({a: int128, b: int128}, implies(b != 0 and a % b == 0, a / b * b == a))
#@ ensures: forall({a: int128, b: int128}, implies(b != 0, a / b * b + a % b == a))
@public
def check():
    pass
