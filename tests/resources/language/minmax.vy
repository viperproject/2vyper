#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

c0: constant(int128) = 12
c1: constant(int128) = min(c0, 5)
c2: constant(int128) = max(c1, c0)


@public
def mn(i: int128, j: int128) -> int128:
    return min(i, j)

@public
def mx(i: int128, j: int128) -> int128:
    return max(i, j)

@public
def mnmx(i: int128, j: int128) -> int128:
    n: int128 = min(i, 5)
    n += max(n, i)
    m: int128 = max(min(min(1, i), min(1, 2)), 5)
    return min(i, max(0, i)) + m + c2