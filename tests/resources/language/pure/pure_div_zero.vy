#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@pure
@private
@constant
def foo(i: int128) -> int128:
    temp: int128 = 0
    if i != 0:
        temp  = i / i
    else:
        temp = 0
    return temp

#@pure
@private
@constant
def foo2(i: int128) -> int128:
    return i / i

#@pure
@private
@constant
def bar(i: int128) -> int128:
    if i != 0:
        if i / i == 1:
            return 1
    return 0

#@pure
@private
@constant
def bar2(i: int128) -> int128:
    if i / i == 1:
        return 1
    return 0

#@pure
@private
@constant
def baz(i: int128) -> int128:
    if i != 0:
        for j in range(1):
            #@ invariant: i / i == 1
            return 1
    return 0


#@ ensures: result(self.foo(4)) == 1
#@ ensures: result(self.foo(0)) == 0
#@ ensures: result(self.foo2(4)) == 1
#@ ensures: revert(self.foo2(0))
#@ ensures: result(self.bar(4)) == 1
#@ ensures: result(self.bar(0)) == 0
#@ ensures: result(self.bar2(4)) == 1
#@ ensures: revert(self.bar2(0))
#@ ensures: result(self.baz(4)) == 1
#@ ensures: result(self.baz(0)) == 0
@public
def test(i: int128):
    pass