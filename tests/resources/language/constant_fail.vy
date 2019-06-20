#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

ZERO: constant(int128) = 0


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() == ZERO
@public
def one() -> int128:
    return 1


#:: ExpectedOutput(not.wellformed:division.by.zero)
#@ ensures: result() == 1 / ZERO
@public
def div_by_ZERO(i: int128) -> int128:
    a: int128 = i / (i * ZERO)
    return a