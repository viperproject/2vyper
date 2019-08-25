#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: no_gas

b: bool
i: int128
u: uint256
d: decimal
bb: bytes32
bts: bytes[10]
s: string[10]


#@ ensures: not self.b
#@ ensures: self.i == 0
#@ ensures: self.u == 0
#@ ensures: self.d == 0.0
#@ ensures: self.bb == EMPTY_BYTES32
#@ ensures: self.bts == b""
#@ ensures: self.s == ""
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.bts == "\0\0\0\0\0\0\0\0\0\0"
@public
def __init__():
    pass
