#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation, no_performs


owner: address
balance_of: map(address, wei_value)
is_private: map(address, bool)


#@ invariant: self.owner == old(self.owner)
#:: Label(ALLOC)
#@ invariant: allocated() == self.balance_of
#:: Label(OFF)
#@ invariant: forall({a: address}, {offered(1, 0, a, self.owner)}, {self.balance_of[a]},
    #@ a != self.owner  ==> offered(1, 0, a, self.owner) == (0 if self.is_private[a] else self.balance_of[a]))


@public
def __init__():
    self.owner = msg.sender


@public
@payable
def deposit():
    #@ offer(1, 0, to=self.owner, times=0 if self.is_private[msg.sender] else msg.value)
    self.balance_of[msg.sender] += msg.value


@public
def set_private():
    self.is_private[msg.sender] = True
    #@ revoke(1, 0, to=self.owner)


#:: ExpectedOutput(invariant.violated:assertion.false, OFF)
@public
def set_private_fail():
    self.is_private[msg.sender] = True


@public
def take_balance(of: address, amount: wei_value):
    assert msg.sender == self.owner
    assert not self.is_private[of]
    
    if of != msg.sender:
        self.balance_of[of] -= amount
        #@ exchange(1, 0, of, self.owner, times=amount)
        self.balance_of[self.owner] += amount


#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, ALLOC)
@public
def take_balance_exchange_fail(of: address, amount: wei_value):
    assert msg.sender == self.owner
    assert not self.is_private[of]

    self.balance_of[of] -= amount
    #:: ExpectedOutput(exchange.failed:no.offer) | ExpectedOutput(carbon)(exchange.failed:insufficient.funds)
    #@ exchange(2, 0, of, self.owner, times=amount)
    self.balance_of[self.owner] += amount


#:: ExpectedOutput(invariant.violated:assertion.false, ALLOC)
@public
def take_balance_fail(of: address, amount: wei_value):
    assert msg.sender == self.owner
    assert not self.is_private[of]

    self.balance_of[of] -= amount
    self.balance_of[self.owner] += amount
