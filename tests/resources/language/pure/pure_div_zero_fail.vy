#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@pure
@private
@constant
def baz(i: int128) -> int128:
    for j in range(1):
        #:: ExpectedOutput(not.wellformed:division.by.zero) | ExpectedOutput(loop.invariant.not.wellformed:division.by.zero)
        #@ invariant: i / i == 1
        return 1
    return 0

#:: ExpectedOutput(silicon)(function.failed:function.revert)
#@ ensures: result(self.baz(4)) == 1
@public
def test(i: int128):
    pass