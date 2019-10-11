#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
def current_gas() -> uint256:
    return msg.gas


@public
def compare_gas():
    cg: uint256 = msg.gas
    ctr: int128
    for i in range(20):
        ctr += 1
    
    #:: ExpectedOutput(assert.failed:assertion.false)
    assert msg.gas == cg, UNREACHABLE
