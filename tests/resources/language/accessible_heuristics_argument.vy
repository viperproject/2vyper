#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


owner: address


#@ invariant: forall({a: address, v: wei_value}, {accessible(a, v)}, implies(v <= self.balance, accessible(a, v)))


@public
def __init__():
    self.owner = msg.sender


@public
@payable
def __default__():
    pass


@public
def withdraw(amount: wei_value):
    send(msg.sender, amount)


@public
def withdraw_none():
    if False:
        send(msg.sender, self.balance)
