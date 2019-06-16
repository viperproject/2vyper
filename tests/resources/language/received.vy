#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

owner: address

balanceOf: map(address, wei_value)


#@ invariant: received(self.owner) == 0
#@ invariant: sum(self.balanceOf) == sum(received())


@public
def __init__():
    self.owner = msg.sender


@public
@payable
def pay():
    assert msg.sender != self.owner
    self.balanceOf[msg.sender] += msg.value

