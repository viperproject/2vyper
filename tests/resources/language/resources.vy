#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


balance_of: map(address, uint256(wei))


#@ resource: GOOD()
#@ resource: ALLOC(owner: address)
#@ resource: DOUBLE(owner1: address, owner2: address)

#@ invariant: allocated() == self.balance_of
#@ invariant: allocated[wei]() == self.balance_of
#@ invariant: forall({a: address}, {allocated[GOOD](a)}, allocated[GOOD](a) == 0)
#@ invariant: forall({a: address, o: address}, allocated[ALLOC(o)](a) == 0)
#@ invariant: forall({a: address, o1: address, o2: address}, allocated[DOUBLE(o1, o2)](a) == 0)


@public
def __init__():
    pass


@public
@payable
def deposit():
    self.balance_of[msg.sender] += msg.value


@public
def transfer(to: address, amount: uint256(wei)):
    self.balance_of[msg.sender] -= amount
    #@ reallocate[wei](amount, to=to, times=1)
    self.balance_of[to] += amount
