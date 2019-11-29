#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from vyper.interfaces import ERC20


token: ERC20
owner: address


@public
def __init__(token_address: address):
    self.token = ERC20(token_address)
    self.owner = msg.sender


@public
def transfer(to: address, token_id: uint256) -> bool:
    return self.token.transfer(to, token_id)
