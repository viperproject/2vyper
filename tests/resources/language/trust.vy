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
#@ invariant: forall({a: address}, {trusted(a, by=self.minter)}, trusted(a, by=self.minter) == self.trusted[a])


@public
def __init__():
    self.minter = msg.sender


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


# @public
# def mint(amount: uint256):
#     assert self.trusted[msg.sender]
 
#     self.balance_of[msg.sender] += amount
#     # create[token](amount, by=)
