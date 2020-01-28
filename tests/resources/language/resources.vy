#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


owner: address
good_creator: address
balance_of: map(address, uint256(wei))
buyers: map(address, bool)


#@ invariant: self.owner == old(self.owner)

#@ resource: GOOD()
#@ resource: ALLOC(owner: address)
#@ resource: DOUBLE(owner1: address, owner2: address)

#@ invariant: allocated() == self.balance_of
#@ invariant: allocated[wei]() == self.balance_of
#@ invariant: forall({a: address}, {allocated[creator(GOOD)](a)}, allocated[creator(GOOD)](a) == (1 if a == self.good_creator else 0))
#@ invariant: forall({a: address}, {allocated[GOOD](a)}, allocated[GOOD](a) == (1 if a == self.owner else 0))
#@ invariant: forall({a: address, o: address}, allocated[ALLOC(o)](a) == 0)
#@ invariant: forall({a: address, o1: address, o2: address}, allocated[DOUBLE(o1, o2)](a) == 0)

#@ invariant: forall({a: address}, self.buyers[a] ==> offered[wei <-> GOOD](self.balance_of[a], 1, a, self.owner) >= 1)
#@ invariant: forall({a: address}, self.buyers[a] ==> offered[GOOD <-> ALLOC(self.owner)](1, 1, a, self.owner) == 10)


@public
def __init__(_good_creator: address):
    self.owner = msg.sender
    self.good_creator = _good_creator
    #@ create[creator(GOOD)](1)
    #@ reallocate[creator(GOOD)](1, to=self.good_creator)
    # This is allowed since the initializer is always allowed to create resources
    #@ create[GOOD](1)


@public
@payable
def deposit():
    assert not self.buyers[msg.sender]

    self.balance_of[msg.sender] += msg.value


@public
def transfer(to: address, amount: uint256(wei)):
    assert not self.buyers[msg.sender]
    assert not self.buyers[to]

    self.balance_of[msg.sender] -= amount
    #@ reallocate[wei](amount, to=to)
    self.balance_of[to] += amount


@public
def offer():
    #@ offer[wei <-> GOOD](self.balance_of[msg.sender], 1, to=self.owner, times=1)
    #@ revoke[GOOD <-> ALLOC(self.owner)](1, 1, to=self.owner)
    #@ offer[GOOD <-> ALLOC(self.owner)](1, 1, to=self.owner, times=10)
    self.buyers[msg.sender] = True


@public
def change_good_creator(to: address):
    assert msg.sender == self.good_creator

    self.good_creator = to
    #@ reallocate[creator(GOOD)](1, to=to)


@public
def do_nothing():
    assert msg.sender == self.good_creator

    #@ create[GOOD](1)
    #@ destroy[GOOD](1)
