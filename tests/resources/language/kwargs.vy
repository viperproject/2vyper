#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: implies(success(), result() == i + j)
@public
def add_numbers(i: int128, j: int128=1) -> int128:
    return i + j


#@ ensures: implies(success(), result() == a)
@public
def get_address(a: address = msg.sender) -> address:
    return a


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() == 0)
@public
def kwargs_fail(i: int128 = 0) -> int128:
    return i
