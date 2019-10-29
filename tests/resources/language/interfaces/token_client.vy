#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import token


owner: address

tk: token
number_of_tokens: uint256

price: wei_value


#@ invariant: self.tk == old(self.tk)
#@ invariant: self.price == old(self.price)
#@ invariant: self.price * (100 - self.number_of_tokens) <= self.balance


@public
def __init__(token_address: address, _price: wei_value):
    self.owner = msg.sender
    self.tk = token(token_address)
    self.number_of_tokens = 100
    self.price = _price

    assert self.tk.balance_of(self) == 100


#@ ensures: implies(success(), _balance_of(self.tk, self) == old(_balance_of(self.tk, self)) - amount)
@public
@payable
def sell(amount: uint256):
    assert msg.value == amount * self.price
    self.number_of_tokens -= amount
    self.tk.transfer(msg.sender, amount)
