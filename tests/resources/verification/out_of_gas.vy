#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success()
@public
def out_of_gas_fail(i: int128) -> int128:
    return 2 * i + 1


#@ ensures: success(if_not=out_of_gas)
#@ ensures: success(if_not=sender_failed)
@public
def out_of_gas(i: int128) -> int128:
    return 3 * i + 2
