#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() == 5
@public
def can_fail(amount: int128) -> int128:
    assert amount > 10
    return 5


#@ ensures: revert() or result() == 5
@public
def can_fail_as_well(amount: int128) -> int128:
    assert amount > 10
    return 5
