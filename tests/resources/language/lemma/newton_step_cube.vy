#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ lemma_def times_4(i: int128):
    #@ i * 2 == i * 1 + i * 1
    #@ i * 4 == i * 2 + i * 2

#@ ensures: success() ==> x > 4 ==> result() <= x
#@ ensures: success() ==> x < 4 ==> result() >= x
@public
@constant
def newtonStep(x: int128) -> int128:
    #@ lemma_assert 3 * x * x - 8 * x + 6 == ((3 * x) - 8) * x + 6
    #@ lemma_assert lemma.times_4(x) and ((3 * x) - 8) * x + 6 > 0
    return x - (x * x * x - 4 * x * x + 6 * x - 24) / (3 * x * x - 8 * x + 6)