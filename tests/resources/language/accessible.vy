#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


owner: address


#@ invariant: accessible(self.owner, self.balance, self.withdraw())
#@ always check: implies(msg.sender != self.owner, self.balance >= old(self.balance))


@public
def __init__():
    self.owner = msg.sender


@public
@payable
def __default__():
    pass


#@ ensures: implies(msg.sender == old(self.owner), success(if_not=out_of_gas or sender_failed))
#@ ensures: implies(success(), implies(msg.sender == old(self.owner), sent(msg.sender) - old(sent(msg.sender)) >= old(self.balance)))
@public
def withdraw():
    assert msg.sender == self.owner
    send(msg.sender, self.balance)
