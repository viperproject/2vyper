#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Verification took   2.77 seconds. [benchmark=10] (With loop invariants)
# Verification took  16.18 seconds. [benchmark=10] (With loop unrolling) Stack Overflow (with l > 14)

l: constant(int128) = 14

#@ ensures: res == (sum(range(l)) + l) * l
@public
def foo(a: int128):
    res: int128 = 0
    for i in range(l):
        #@ invariant: res == (sum(range(l)) + l) * loop_iteration(i)
        t: int128 = 0
        for j in range(l):
            #@ invariant: t == sum(previous(j)) + loop_iteration(j)
            t += j + 1
        res += t
