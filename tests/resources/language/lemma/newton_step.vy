#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ lemma_def mul_sign(x: int128):
    #@ x >  0 ==> 1 * x >  0
    #@ x <  0 ==> 1 * x <  0
    #@ x == 0 ==> 1 * x == 0

#@ ensures: success() ==> x >  2 ==> result() <= x
#@ ensures: success() ==> x == 2 ==> result() == x
# ensures: success() ==> x <  2 ==> result() >= x
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success() ==> x <  2 ==> result() == x
@public
@constant
def newtonStep(x: int128) -> int128:
    if x == 2:
        return x

    #@ lemma_assert lemma.mul_sign(x)
    #@ lemma_assert x > 2 ==> x - ((x * x - 4 * x + 4) / (2 * x - 4)) <= x
    #@ lemma_assert (x == 1 or x == 0) ==> x - ((x * x - 4 * x + 4) / (2 * x - 4)) == 1
    return x - ((x * x - 4 * x + 4) / (2 * x - 4))
