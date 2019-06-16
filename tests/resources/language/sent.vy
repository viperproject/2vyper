#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

reward: wei_value
should_pay: bool

owner: address


#@ always ensures: implies(msg.sender != self.owner, self.should_pay == old(self.should_pay))

#@ invariant: self.owner == old(self.owner)
#@ invariant: self.balance >= self.reward
#@ invariant: implies(old(self.should_pay), self.should_pay)
#@ invariant: sent(self.owner) == 0
#:: Label(SU)
#@ invariant: implies(not self.should_pay, sum(sent()) == 0)


@public
@payable
def __init__(_reward: wei_value):
    assert msg.value >= _reward
    self.reward = _reward
    self.owner = msg.sender


@public
def approve_payment():
    assert msg.sender == self.owner
    self.should_pay = True


@public
def send_fail():
    assert msg.sender != self.owner
    to_send: wei_value = self.reward
    self.reward = 0
    #:: ExpectedOutput(call.invariant:assertion.false, SU)
    send(msg.sender, to_send)


@public
def get_payment():
    assert msg.sender != self.owner
    assert self.should_pay
    to_send: wei_value = self.reward
    self.reward = 0
    send(msg.sender, to_send)


@public
def send_payment():
    assert msg.sender == self.owner
    assert self.owner != 1
    self.should_pay = True
    to_send: wei_value = self.reward
    self.reward = 0
    send(1, to_send)