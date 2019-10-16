#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: success(if_not=out_of_gas)
@public
def no_overflow(a: int128) -> int128:
    if a >= 0:
        return a - 10
    else:
        return a + 10


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success(if_not=out_of_gas)
@public
def no_overflow_fail(a: int128) -> int128:
    if a >= 0:
        return a + 10
    else:
        return a - 10


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success(if_not=out_of_gas)
@public
def no_overflow_neg_fail(a: int128) -> int128:
    return -a
