#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ ensures: res == 300
@public
def foo(a: int128):
    res: int128 = 0
    if a == 0:
        for i in range(300):
            #@ invariant: res == i
            res += 1
    else:
        res += 300

#@pure
@private
@constant
def bar(a: int128) -> int128:
    res: int128 = 0
    if a == 0:
        for i in range(300):
            #@ invariant: res == i
            res += 1
    else:
        res += 300
    return res

#@ ensures: res == 300
@public
def baz(a: int128):
    res: int128 = self.bar(a)
