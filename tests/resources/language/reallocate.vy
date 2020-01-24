#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


balance_of: map(address, wei_value)


#:: Label(AB)
#@ invariant: allocated() == self.balance_of
#@ invariant: forall({a: address}, allocated(a) == self.balance_of[a])


@public
def __init__():
    pass


@public
@payable
def deposit():
    self.balance_of[msg.sender] += msg.value


@public
def withdraw(amount: wei_value):
    self.balance_of[msg.sender] -= amount
    send(msg.sender, amount)


#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, AB)
@public
def withdraw_fail():
    amount: wei_value = self.balance_of[msg.sender]
    #:: ExpectedOutput(call.invariant:assertion.false, AB)
    send(msg.sender, amount)
    self.balance_of[msg.sender] = 0


@public
def transfer(to: address, amount: wei_value):
    self.balance_of[msg.sender] -= amount
    #@ reallocate(amount, to=to)
    self.balance_of[to] += amount


#:: ExpectedOutput(invariant.violated:assertion.false, AB)
@public
def transfer_no_realloc_fail(to: address, amount: wei_value):
    self.balance_of[msg.sender] -= amount
    self.balance_of[to] += amount


#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, AB)
@public
def transfer_no_funds_fail(to: address, amount: wei_value):
    self.balance_of[msg.sender] -= amount
    #:: ExpectedOutput(reallocate.failed:insufficient.funds)
    #@ reallocate(2 * amount, to=to)
    self.balance_of[to] += amount
