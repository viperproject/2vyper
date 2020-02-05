#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation, no_performs


#@ resource: good()


#@ invariant: forall({a: address}, {allocated[wei](a)}, allocated[wei](a) == 0)
#:: Label(INV)
#@ invariant: forall({a: address}, {allocated[good](a)}, allocated[good](a) == 0)


@public
def non_injective_offer():
    #:: ExpectedOutput(offer.failed:offer.not.injective)
    #@ foreach({i: uint256}, offer(i % 2, i % 2, to=ZERO_ADDRESS, times=i))
    pass


@public
def injective_offer_all_zero():
    #@ foreach({i: uint256}, offer(i % 2, i % 2, to=ZERO_ADDRESS, times=0))
    pass


#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, INV)
@public
def non_injective_create():
    #:: ExpectedOutput(create.failed:offer.not.injective) | ExpectedOutput(carbon)(create.failed:not.a.creator)
    #@ foreach({a: address, i: int128}, create[good](i, to=a if i > 12 else ZERO_ADDRESS))
    pass
