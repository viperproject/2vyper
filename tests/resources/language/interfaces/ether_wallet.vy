#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import wallet

implements: wallet


balance_of: map(address, wei_value)


#@ invariant: sum(self.balance_of) <= self.balance
#@ invariant: forall({a: address, v: wei_value}, {accessible(a, v, self.withdraw(v))}, implies(v <= self.balance_of[a], accessible(a, v, self.withdraw(v))))

#@ always check: forall({a: address}, {sent(a)}, implies(a != msg.sender, sent(a) == old(sent(a))))


@public
@payable
def deposit():
    self.balance_of[msg.sender] = msg.value


@public
def withdraw(amount: wei_value):
    self.balance_of[msg.sender] -= amount
    send(msg.sender, amount)
