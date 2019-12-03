#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract C:
    def pay(): modifying


pending_returns: map(address, wei_value)


@public
@payable
@nonreentrant('lock')
def deposit():
    self.pending_returns[msg.sender] += msg.value


@public
@nonreentrant('lock')
def withdraw():
    C(msg.sender).pay(value=self.pending_returns[msg.sender])
    self.pending_returns[msg.sender] = 0
