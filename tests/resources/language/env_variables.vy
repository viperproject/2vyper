#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
@payable
def test_env():
    cb: address = block.coinbase
    df: uint256 = block.difficulty
    no: uint256 = block.number
    ph: bytes32 = block.prevhash
    tt: timestamp = block.timestamp
    sd: address = msg.sender
    vl: wei_value = msg.value
    og: address = tx.origin
