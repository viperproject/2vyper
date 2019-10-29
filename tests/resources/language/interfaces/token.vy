#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ interface


#@ ghost:
    #@ def _balance_of(a: address) -> uint256: ...


#@ ensures: implies(success(), result() == _balance_of(self, a))
@public
@constant
def balance_of(a: address) -> uint256:
    raise "Not implemented"


# ensures: implies(msg.sender == to or to == ZERO_ADDRESS, not success())
# ensures: implies(_balance_of(self, msg.sender) < amount, not success())
# ensures: _balance_of(self, msg.sender) == old(self.balance_of(msg.sender)) - amount
# ensures: _balance_of(self, to) == old(_balance_of(self, msg.sender)) + amount
@public
@payable
def transfer(to: address, amount: uint256):
    raise "Not implemented"
