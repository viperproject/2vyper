#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

a: int128

#@pure
@private
@constant
def add_1(i: int128) -> int128:
    if i > 1:
        if i > 2:
            if i > 3:
                if i > 4:
                    return i + 1
    assert False
    return 0

#@pure
@private
@constant
def mul_10(i: int128) -> int128:
    return i * 10


#@pure
@private
@constant
def foo(i: int128) -> int128:
    temp: int128 = i
    if i > 1:
        temp = self.add_1(i)
    return self.add_1(temp)


#@ ensures: i <= 4 ==> revert()
#@ ensures: i > 4 and i <= (MAX_INT128 - 2) ==> success(if_not=out_of_gas)
#@ ensures: result(self.foo(result(self.foo(5)) - 2)) == 7
@public
def bar(i: int128):
    self.foo(i)


#:: ExpectedOutput(function.failed:function.revert)
#@ ensures: result(self.foo(4)) == 6
@public
def bar_fail():
    pass
