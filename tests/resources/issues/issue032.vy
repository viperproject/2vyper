#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Similar to nonreentrant.vy test

contract C:
    def pay(): modifying


pending_returns: map(address, wei_value)


#@ preserves:
    #:: Label(CONSTANT_SENT)
    #@ always ensures: locked('lock') ==> sent() == old(sent())
    #@ always ensures: locked('lock') ==> self.pending_returns == old(self.pending_returns)


@public
@payable
@nonreentrant('lock')
def deposit():
    self.pending_returns[msg.sender] += msg.value


#@ ensures: old(locked('lock')) ==> revert()
#@ ensures: success() ==> sent(msg.sender) - old(sent(msg.sender)) == old(self.pending_returns[msg.sender])
@public
@nonreentrant('lock')
def withdraw():
    C(msg.sender).pay(value=self.pending_returns[msg.sender])
    self.pending_returns[msg.sender] = 0


#:: ExpectedOutput(postcondition.violated:assertion.false, CONSTANT_SENT)
@public
@nonreentrant('lck')
def withdraw_fail():
    amount: wei_value = self.pending_returns[msg.sender]
    self.pending_returns[msg.sender] = 0
    C(msg.sender).pay(value=amount)
