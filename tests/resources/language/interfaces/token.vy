#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ interface


# pure
@public
def balance_of(a: address) -> uint256:
    raise "Not implemented"


# ensures: implies(msg.sender == to or to == ZERO_ADDRESS, not success())
# ensures: implies(self.balance_of(msg.sender) < amount, not success())
# ensures: self.balance_of(msg.sender) == old(self.balance_of(msg.sender)) - amount
# ensures: self.balance_of(to) == old(self.balance_of(msg.sender)) + amount
@public
@payable
def transfer(to: address, amount: uint256):
    raise "Not implemented"
