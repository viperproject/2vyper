#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: not out_of_gas() ==> success()
@public
def gas_success(i: int128) -> int128:
    return i


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: not out_of_gas()
@public
def gas_success_fail(i: int128) -> int128:
    return i


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: out_of_gas()
@public
def gas_fail_fail(i: int128) -> int128:
    return i
