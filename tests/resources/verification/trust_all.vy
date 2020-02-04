#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


owner: address
address_map: map(int128, address)


#@ invariant: forall({a: address}, {allocated(a)}, allocated(a) == 0)
#@ invariant: forall({a: address}, {trusted(a, by=self.owner)}, trusted(a, by=self.owner))


@public
def __init__():
    self.owner = msg.sender
    #@ foreach({a: address}, trust(a, True))


@public
def offer(to: address):
    #@ offer(1, 1, to=to, acting_for=self.owner, times=1)
    pass


@public
def offer_all(to: address):
    #@ foreach({amount: uint256}, offer(amount, amount, to=to, acting_for=self.owner, times=1))
    pass


@public
def set_address(a: address, f: int128):
    self.address_map[f] = a


@public
def trust_all():
    assert msg.sender != self.owner
    
    #:: ExpectedOutput(trust.failed:trust.not.injective)
    #@ foreach({i: int128}, trust(self.address_map[i % 2], True))
