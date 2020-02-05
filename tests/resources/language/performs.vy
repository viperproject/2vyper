#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


minter: address
balance_of: map(address, uint256)


#@ resource: token()


#@ invariant: sum(allocated[wei]()) == 0
#@ invariant: allocated[token]() == self.balance_of

#@ invariant: allocated[creator(token)](self.minter) == 1


#@ performs: create[creator(token)](1)
#@ performs: create[token](1)
@public
def __init__():
    self.minter = msg.sender
    #@ create[creator(token)](1)
    self.balance_of[msg.sender] += 1
    #@ create[token](1)


#@ performs: create[token](amount, to=to)
@public
def mint(amount: uint256, to: address):
    assert msg.sender == self.minter

    self.balance_of[to] += amount
    #@ create[token](amount, to=to)


@public
def mint_no_performs_fail(amount: uint256, to: address):
    assert msg.sender == self.minter

    self.balance_of[to] += amount
    #:: ExpectedOutput(create.failed:no.performs)
    #@ create[token](amount, to=to)


#@ performs: create[token](amount, to=to)
#:: ExpectedOutput(performs.leakcheck.failed:performs.leaked)
@public
def mint_no_create_fail(amount: uint256, to: address):
    assert msg.sender == self.minter


#@ performs: offer[token <-> wei](1, 2, to=to, times=3)
@public
def offer(to: address):
    pass
    #@ offer[token <-> wei](1, 2, to=to, times=3)


@public
def offer_no_performs_fail(to: address):
    pass
    #:: ExpectedOutput(offer.failed:no.performs)
    #@ offer[token <-> wei](1, 2, to=to, times=3)


#@ performs: offer[token <-> wei](1, 2, to=to, times=3)
#:: ExpectedOutput(performs.leakcheck.failed:performs.leaked)
@public
def offer_no_offer_fail(to: address):
    pass


#@ performs: revoke[token <-> wei](1, 2, to=to)
@public
def revoke(to: address):
    pass
    #@ revoke[token <-> wei](1, 2, to=to)


@public
def revoke_no_performs_fail(to: address):
    pass
    #:: ExpectedOutput(revoke.failed:no.performs)
    #@ revoke[token <-> wei](1, 2, to=to)


#@ performs: revoke[token <-> wei](1, 2, to=to)
#:: ExpectedOutput(performs.leakcheck.failed:performs.leaked)
@public
def revoke_no_revoke_fail(to: address):
    pass


#@ performs: trust(a, True)
@public
def trust(a: address):
    pass
    #@ trust(a, True)


@public
def trust_no_performs_fail(a: address):
    pass
    #:: ExpectedOutput(trust.failed:no.performs)
    #@ trust(a, True)


#@ performs: trust(a, True)
#:: ExpectedOutput(performs.leakcheck.failed:performs.leaked)
@public
def trust_no_trust_fail(a: address):
    pass
