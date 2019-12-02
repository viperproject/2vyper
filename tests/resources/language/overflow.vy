#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: not out_of_gas() and not overflow() ==> success()
@public
def overflow_success(i: int128) -> int128:
    return 2 * i


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: not overflow() ==> success()
@public
def overflow_success_fail(i: int128) -> int128:
    return 2 * i


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: not out_of_gas() ==> success()
@public
def gas_success_fail(i: int128) -> int128:
    return 2 * i


#@ ensures: not overflow()
@public
def no_overflow(i: int128) -> int128:
    if i < 0:
        return i + 21
    else:
        return i - 42


#@ ensures: success() ==> not overflow()
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: not overflow()
@public
def no_overflow_fail(i: int128) -> int128:
    if i > 0:
        return i + 21
    else:
        return i - 42
