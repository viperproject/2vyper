#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@pure
@private
@constant
def foo(a: bool) -> int128:
    res: int128 = 0
    for i in range(10000):
        #@ invariant: loop_iteration(i) <= 4
        #@ invariant: loop_iteration(i) <= 3 ==> res == 0
        #@ invariant: loop_iteration(i) > 3 ==> res == 3
        if a:
            break
        if i == 4:
            break
            continue
        if i == 2:
            continue
        if i == 1:
            continue
        res += i
        continue
        break
    return res


#@ ensures: result(self.foo(False)) == 3
#@ ensures: result(self.foo(True)) == 0
@public
def bar(i: int128):
    pass

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result(self.foo(False)) != 3
@public
def bar_fail(i: int128):
    pass