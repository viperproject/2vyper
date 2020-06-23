#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@pure
@private
@constant
def bar() -> int128:
    res: int128 = 0
    for i in range(10000):
        #:: ExpectedOutput(invalid.program:invalid.pure)
        #@ invariant: success(self.baz())
        #@ invariant: False
        if i == 4:
            break
        if i <= 2:
            continue
        res += i
    return res

#@pure
@private
@constant
def baz() -> int128:
    return self.bar()


#@ ensures: success(self.bar())
@public
def foo(i: int128):
    pass