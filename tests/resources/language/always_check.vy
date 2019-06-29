#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


f: int128
owner: address


#:: Label(CHECK1)
#@ always check: implies(msg.sender != self.owner, self.f == old(self.f))
#:: Label(CHECK2)
#@ always check: implies(msg.sender != self.owner, sum(sent()) == old(sum(sent())))


@public
@payable
def __init__():
    self.owner = msg.sender


@public
def set_f(new_f: int128):
    assert msg.sender == self.owner
    self.f = new_f


#:: ExpectedOutput(check.violated:assertion.false, CHECK1)
@public
def set_f_fail(new_f: int128):
    self.f = new_f


@public
def pay(amount: wei_value, to: address):
    assert msg.sender == self.owner
    send(to, amount)


@public
def pay_fail(amount: wei_value, to: address):
    #:: ExpectedOutput(call.check:assertion.false, CHECK2)
    send(to, amount)


@public
def pay_and_set_f(amount: wei_value, to: address, new_f: int128):
    assert msg.sender == self.owner
    self.f = new_f
    send(to, amount)


@public
def pay_and_set_f_fail_1(amount: wei_value, to: address, new_f: int128):
    self.f = new_f
    #:: ExpectedOutput(call.check:assertion.false, CHECK1) | ExpectedOutput(carbon)(call.check:assertion.false, CHECK2)
    send(to, amount)


#:: ExpectedOutput(carbon)(check.violated:assertion.false, CHECK1)
@public
def pay_and_set_f_fail_2(amount: wei_value, to: address, new_f: int128):
    #:: ExpectedOutput(call.check:assertion.false, CHECK2)
    send(to, amount)
    self.f = new_f


#@ ensures: self.f == old(self.f)
#:: ExpectedOutput(carbon)(check.violated:assertion.false, CHECK1)
@public
def pay_and_set_f_fail_3(amount: wei_value, to: address, new_f: int128):
    temp: int128 = self.f
    self.f = new_f
    #:: ExpectedOutput(call.check:assertion.false, CHECK1) | ExpectedOutput(carbon)(call.check:assertion.false, CHECK2)
    send(to, amount)
    self.f = temp
