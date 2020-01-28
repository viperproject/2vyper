#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


owner: address
minters: map(address, bool)

balance_of: map(address, uint256)


#@ resource: token()

#@ invariant: self.owner == old(self.owner)
#@ invariant: sum(allocated[wei]()) == 0
#@ invariant: self.balance_of == allocated[token]()
#@ invariant: forall({a: address}, {self.minters[a]}, {allocated[creator(token)](a)},
    #@ self.minters[a] == (allocated[creator(token)](a) > 0))
#@ invariant: forall({a: address}, allocated[creator(creator(token))](a) == (1 if a == self.owner else 0))


@public
def __init__():
    self.owner = msg.sender

    #@ create[creator(creator(token))](1)
    #@ create[creator(token)](1)
    self.minters[self.owner] = True


@public
def make_minter(a: address):
    assert msg.sender == self.owner

    #@ create[creator(token)](1)
    #@ reallocate[creator(token)](1, to=a)

    self.minters[a] = True


@public
def make_minter_fail(a: address):
    #:: ExpectedOutput(create.failed:not.a.creator)
    #@ create[creator(token)](1)
    #@ reallocate[creator(token)](1, to=a)

    self.minters[a] = True


@public
def mint(amount: uint256):
    assert self.minters[msg.sender]
    #@ create[token](amount)
    self.balance_of[msg.sender] += amount
