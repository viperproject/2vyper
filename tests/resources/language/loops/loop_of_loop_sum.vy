#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Verification took   2.96 seconds. [benchmark=10] (With loop invariants)
# Verification took  24.97 seconds. [benchmark=10] (With loop unrolling) Stack Overflow (with l > 14)

l: constant(int128) = 14
m: constant(int128) = l + 1

#@ ensures: res == (sum(range(l)) + l) * (l + 1) + (l + 1)
@public
def foo(a: int128):
    res: int128 = 0
    for i in range(l):
        #@ invariant: old(res) == 0
        #@ invariant: res == (sum(range(l)) + l) * loop_iteration(i)
        for j in range(l):
            #@ invariant: res == old(res) + sum(previous(j)) + loop_iteration(j)
            res += j + 1

    for i in range(m):
        #@ invariant: res == old(res) + sum(previous(i)) + loop_iteration(i)
        res += i + 1
