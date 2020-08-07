#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

N_COINS: constant(int128) = 3

#@ ensures: success() ==> result() <= start
@public
@constant
def get_y(start: uint256, b: uint256, c: uint256) -> uint256:
    assert start >= 2 * c
    assert b > 0
    assert c > 0
    y_prev: uint256 = start
    y: uint256 = start
    for _i in range(255):
        #@ invariant: y <= y_prev and y_prev <= old(y)
        #@ invariant: y >= c
        y_prev = y
        y = (y * y + c) / (2 * y + b)


        #@ lemma_assert y_prev * y_prev + c <= y_prev * y_prev + 1 * y_prev
        #@ lemma_assert (y_prev * y_prev + 1 * y_prev) / (2 * y_prev + b) <= (y_prev * y_prev + 1 * y_prev) / (2 * y_prev)
        #@ lemma_assert (y_prev * y_prev + 1 * y_prev) / (2 * y_prev + b) <= y_prev * (2 * y_prev) / (2 * y_prev)

        # Equality with the precision of 1
        if y > y_prev:
            if y - y_prev <= 1:
                break
        else:
            if y_prev - y <= 1:
                break
        if y < c:
            break
    return y