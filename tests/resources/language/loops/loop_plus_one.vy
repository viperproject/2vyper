#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Verification took   1.88 seconds. [benchmark=10] (With loop invariants)
# Verification took   6.48 seconds. [benchmark=10] (With loop unrolling) Stack Overflow (with loop iterations > 220)

#@ ensures: res == 220
@public
def foo(a: int128):
    res: int128 = 0
    for i in range(300):
        #@ invariant: res == i
        #@ invariant: i <= 220
        t: int128 = 0
        if i == 220:
            break
        res += 1
        if i > 255:
            continue
