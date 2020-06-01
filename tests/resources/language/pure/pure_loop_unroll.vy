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
    for i in range(6):
        if a:
            break
        if i == 4:
            break
            continue
        if i == 1:
            continue
        res += i
        continue
        break
    return res

#@pure
@private
@constant
def bar() -> int128:
    res: int128 = 0
    for i in range(6):
        continue
        res += i
    for i in range(6):
        break
        res += i
    for i in range(6):
        res += i
        if False:
            continue
        if False:
            break
    return res


#@ ensures: result(self.foo(False)) == 5
#@ ensures: result(self.foo(True)) == 0
#@ ensures: result(self.bar()) == 15
@public
def test(i: int128):
    pass

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result(self.foo(False)) != 5
@public
def foo_fail(i: int128):
    pass

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result(self.bar()) != 15
@public
def bar_fail(i: int128):
    pass
