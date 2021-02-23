#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: res == 42
@public
def foo(a: int128):
    res: int128 = 0
    if a == 0:
        res += 1
        for i in range(300):
            #@ invariant: res > 0
            res += 1
        res -= 1
    else:
        res += 42

#@pure
@private
@constant
def bar(a: int128) -> int128:
    res: int128 = 0
    if a == 0:
        res += 1
        for i in range(300):
            #@ invariant: res > 0
            res += 1
        res -= 1
    else:
        res += 42
    return res

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: res == 42
@public
def baz(a: int128):
    res: int128 = self.bar(a)
