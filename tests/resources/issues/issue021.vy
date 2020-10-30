#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

uint256_list: uint256[1]
address_list: address[1]
bytes32_list: bytes32[1]

@public
def foo():
    self.uint256_list = [1]
    self.address_list = [0x0000000000000000000000000000000000000001]
    self.bytes32_list = [0x0000000000000000000000000000000000000000000000000000000000000001]

@public
def bar():
    for i in [1, 2, 3]:
        a: int128 = i
    for i in [340282366920938463463374607431768211456]:
        b: uint256 = i
