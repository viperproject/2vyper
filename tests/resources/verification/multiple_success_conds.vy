#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: success(if_not=out_of_gas or overflow)
@public
def inc(i: int128) -> int128:
    return i + 1


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success(if_not=out_of_gas or overflow)
@public
def inc_fail(i: int128) -> int128:
    assert i % 2 == 0
    return i + 1
