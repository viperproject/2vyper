#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


minter: address
balance_of: map(address, uint256)
trusted: map(address, bool)


#@ resource: token()


#@ invariant: sum(allocated[wei]()) == 0
#@ invariant: allocated[token]() == self.balance_of
#@ invariant: allocated[creator(token)](self.minter) == 1
#@ invariant: forall({a: address}, {trusted(a, by=self.minter)}, trusted(a, by=self.minter) == self.trusted[a])


@public
def __init__():
    self.minter = msg.sender
    #@ create[creator(token)](1)


@public
def trust(a: address):
    assert msg.sender == self.minter

    self.trusted[a] = True
    #@ trust(a, True)


@public
def untrust(a: address):
    assert msg.sender == self.minter

    self.trusted[a] = False
    #@ trust(a, False)


@public
def mintFrom(amount: uint256):
    assert self.trusted[msg.sender]
 
    self.balance_of[msg.sender] += amount
    #@ create[token](amount, to=msg.sender, by=self.minter)


@public
def mintFrom_fail(amount: uint256): 
    self.balance_of[msg.sender] += amount
    #:: ExpectedOutput(create.failed:not.trusted)
    #@ create[token](amount, to=msg.sender, by=self.minter)


@public
def transferFromMinter(amount: uint256, to: address):
    assert self.trusted[msg.sender]

    self.balance_of[self.minter] -= amount
    #@ reallocate[token](amount, to=to, by=self.minter)
    self.balance_of[to] += amount


@public
def transferFromMinter_fail(amount: uint256, to: address):
    self.balance_of[self.minter] -= amount
    #:: ExpectedOutput(reallocate.failed:not.trusted)
    #@ reallocate[token](amount, to=to, by=self.minter)
    self.balance_of[to] += amount


@public
def burnFromMinter(amount: uint256):
    assert self.trusted[msg.sender]

    self.balance_of[self.minter] -= amount
    #@ destroy[token](amount, by=self.minter)


@public
def burnFromMinter_fail(amount: uint256):
    self.balance_of[self.minter] -= amount
    #:: ExpectedOutput(destroy.failed:not.trusted)
    #@ destroy[token](amount, by=self.minter)


@public
def offerFromMinter(to: address):
    assert self.trusted[msg.sender]

    #@ offer[token <-> token](1, 1, to=to, by=self.minter, times=1)


@public
def offerFromMinter_fail(to: address):
    pass
    #:: ExpectedOutput(offer.failed:not.trusted)
    #@ offer[token <-> token](1, 1, to=to, by=self.minter, times=1)


@public
def revokeFromMinter(to: address):
    assert self.trusted[msg.sender]

    #@ revoke[token <-> token](1, 1, to=to, by=self.minter)


@public
def revokeFromMinter_fail(to: address):
    pass
    #:: ExpectedOutput(revoke.failed:not.trusted)
    #@ revoke[token <-> token](1, 1, to=to, by=self.minter)
