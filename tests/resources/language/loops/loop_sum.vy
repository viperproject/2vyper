#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

l: constant(int128) = 18446744073709551615

#@ ensures: res == sum(range(l)) + l
@public
def foo(a: int128):
    res: int128 = 0
    for i in range(l):
        #@ invariant: res == sum(previous(i)) + loop_iteration(i)
        res += i + 1
