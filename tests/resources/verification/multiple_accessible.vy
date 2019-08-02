#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


owner: address
client: address


#@ invariant: forall({a: address}, {sent(a)}, sent(a) >= old(sent(a)))
#@ invariant: accessible(self.owner, self.balance, self.withdraw())
#@ invariant: accessible(self.client, self.balance, self.withdraw())
#@ invariant: accessible(self.owner, self.balance, self.withdraw()) and accessible(self.client, self.balance, self.withdraw())

#@ invariant: accessible(self.owner, self.balance, self.withdraw_owner())
#:: Label(INV)
#@ invariant: accessible(self.client, self.balance, self.withdraw_owner())


@public
def __init__(_client: address):
    self.owner = msg.sender
    self.client = _client


@public
@payable
def __default__():
    pass


@public
def withdraw():
    send(msg.sender, self.balance)


#:: ExpectedOutput(invariant.violated:assertion.false, INV)
@public
def withdraw_owner():
    assert msg.sender == self.owner
    send(self.owner, self.balance)
