#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@pure
@private
@constant
def foo() -> int128:
    res: int128 = 0
    for i in range(10000):
        #@ invariant: loop_iteration(i) <= 3 ==> res == 0
        #:: ExpectedOutput(loop.invariant.not.preserved:assertion.false)
        #@ invariant: loop_iteration(i) > 3 ==> res == 3
        if i == 4:
            break
        if i <= 2:
            continue
        res += i
    return res

#@pure
@private
@constant
def bar() -> int128:
    res: int128 = 0
    for i in range(10000):
        #:: ExpectedOutput(loop.invariant.not.established:assertion.false)
        #@ invariant: False
        if i == 4:
            break
        if i <= 2:
            continue
        res += i
    return res


#@ ensures: success(self.foo())
#@ ensures: success(self.bar())
@public
def baz(i: int128):
    pass