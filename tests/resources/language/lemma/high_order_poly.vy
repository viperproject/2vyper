#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ requires: b == c + d
#@ lemma_def distributive(a: uint256, b: uint256, c: uint256, d: uint256):
    #@ a * b == a * c + a * d

#@ lemma_def mul_recursive_step(i: uint256, j: uint256):
    #@ j > 0 ==> lemma.distributive(i, j, j - 1, 1)
    #@ j < MAX_UINT256 ==> lemma.distributive(i, j + 1, j, 1)
    #@ i > 0 ==> lemma.distributive(j, i, i - 1, 1)
    #@ i < MAX_UINT256 ==> lemma.distributive(j, i + 1, i, 1)

#@ lemma_def times_400(i: uint256):
    #@ lemma.distributive(i,   2,   1,   1)
    #@ lemma.distributive(i,   4,   2,   2)
    #@ lemma.distributive(i,   8,   4,   4)
    #@ lemma.distributive(i,  16,   8,   8)
    #@ lemma.distributive(i,  10,   2,   8)
    #@ lemma.distributive(i,  32,  16,  16)
    #@ lemma.distributive(i,  40,   8,  32)
    #@ lemma.distributive(i,  50,  40,  10)
    #@ lemma.distributive(i, 100,  50,  50)
    #@ lemma.distributive(i, 200, 100, 100)


#@ ensures: success() ==> result() <= 63362376
#@ ensures: success() ==> x >= 4
@public
@constant
def get_y(x:uint256) -> uint256:
    assert x <= 400
    #@ lemma_assert lemma.times_400(400) and lemma.times_400(400 * 400)
    #@ lemma_assert 400 * 400 * 400 - 4 * 400 * 400 + 6 * 400 - 24 == 63362376
    #@ lemma_assert (400 - 4) * (400 * 400) + 6 * 400 - 24 == 63362376
    #@ lemma_assert x * x * x - 4 * x * x + 6 * x - 24 == x * (x * x) - 4 * (x * x) + 6 * x - 24
    #@ lemma_assert x * (x * x) - 4 * (x * x) + 6 * x - 24 == (x - 4) * (x * x) + 6 * x - 24
    #@ lemma_assert x >= 4 ==> x * x * x - 4 * x * x + 6 * x - 24 <= 63362376
    #@ lemma_assert lemma.mul_recursive_step(3, 3) and lemma.mul_recursive_step(3, 5) \
        #@ and lemma.mul_recursive_step(3, 7) and lemma.mul_recursive_step(3, 9)
    #@ lemma_assert x < 4 ==> x * x * x - 4 * x * x + 6 * x - 24 < 0
    return x * x * x - 4 * x * x + 6 * x - 24