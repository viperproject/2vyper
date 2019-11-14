#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: no_gas


@public
@payable
def __init__():
    pass


#@ ensures: independent(result(), a)
#@ ensures: independent(result(), b)
@public
def get_42(a: int128, b: int128) -> int128:
    return 42


#@ ensures: independent(result(), a)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: independent(result(), b)
@public
def get_42_fail(a: int128, b: int128) -> int128:
    if b > 0:
        return  42
    else:
        return -42


#@ ensures: independent(result(), old(self))
@public
def self_independent(a: int128) -> int128:
    return a


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: independent(result(), old(self))
@public
def self_independent_fail(a: int128) -> int128:
    return a + convert(as_unitless_number(self.balance), int128)
