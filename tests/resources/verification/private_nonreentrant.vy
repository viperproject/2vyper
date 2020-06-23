#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract C:
    def pay(): modifying


pending_returns: map(address, wei_value)


#@ preserves:
    #@ always ensures: old(locked('lock')) ==> locked('lock')
    #:: ExpectedOutput(postcondition.violated:assertion.false, CALL)
    #@ always ensures: old(locked('lock')) ==> sent() == old(sent())
    #@ always ensures: old(locked('lock')) ==> self.pending_returns == old(self.pending_returns)


@public
@payable
@nonreentrant('lock')
def deposit():
    self.pending_returns[msg.sender] += msg.value


@private
@nonreentrant('lock')
def _withdraw(a: address):
    C(a).pay(value=self.pending_returns[a])
    self.pending_returns[a] = 0


#@ ensures: old(locked('lock')) ==> revert()
#@ ensures: success() ==> sent(msg.sender) - old(sent(msg.sender)) == old(self.pending_returns[msg.sender])
@public
def withdraw():
    self._withdraw(msg.sender)


#@ ensures: revert()
@public
@nonreentrant('lock')
def withdraw_revert():
    self._withdraw(msg.sender)


@private
def _withdraw_fail(a: address):
    C(a).pay(value=self.pending_returns[a])
    self.pending_returns[a] = 0


@public
def withdraw_fail():
    #:: Label(CALL)
    self._withdraw_fail(msg.sender)