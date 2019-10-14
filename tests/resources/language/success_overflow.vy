#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


#@ ensures: success(if_not=overflow)
@public
def add_numbers(a: int128, b: int128) -> int128:
    return a + b


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success()
@public
def add_numbers_fail(a: int128, b: int128) -> int128:
    return a + b
