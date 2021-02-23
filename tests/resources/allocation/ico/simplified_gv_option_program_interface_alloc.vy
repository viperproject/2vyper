#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

#@ interface

import tests.resources.allocation.ico.gv_option_token_interface_alloc as GVOT

option30perCent: constant(uint256) = 26 * 10 ** 16 # GVOT30 tokens per usd cent during option purchase
option20perCent: constant(uint256) = 24 * 10 ** 16 # GVOT20 tokens per usd cent during option purchase
option10perCent: constant(uint256) = 22 * 10 ** 16 # GVOT10 tokens per usd cent during option purchase
token30perCent: constant(uint256)  = 13684210526315800  # GVT tokens per usd cent during execution of GVOT30
token20perCent: constant(uint256)  = 12631578947368500  # GVT tokens per usd cent during execution of GVOT20
token10perCent: constant(uint256)  = 11578947368421100  # GVT tokens per usd cent during execution of GVOT10

#@ ghost:
    #@ def gvOptionToken30() -> GVOT: ...
    #@ def gvOptionToken20() -> GVOT: ...
    #@ def gvOptionToken10() -> GVOT: ...
    #@ def ico() -> address: ...
    #@ def init() -> bool: ...

#@ invariant: ico(self) == old(ico(self))
#@ invariant: old(gvOptionToken30(self)) != ZERO_ADDRESS ==> gvOptionToken30(self) != ico(self)
# invariant: old(gvOptionToken20(self)) != ZERO_ADDRESS ==> gvOptionToken20(self) != ico(self)
# invariant: old(gvOptionToken10(self)) != ZERO_ADDRESS ==> gvOptionToken10(self) != ico(self)
#@ invariant: old(gvOptionToken30(self)) != ZERO_ADDRESS ==> gvOptionToken30(self) == old(gvOptionToken30(self))
# invariant: old(gvOptionToken20(self)) != ZERO_ADDRESS ==> gvOptionToken20(self) == old(gvOptionToken20(self))
# invariant: old(gvOptionToken10(self)) != ZERO_ADDRESS ==> gvOptionToken10(self) == old(gvOptionToken10(self))
#@ inter contract invariant: gvOptionToken30(self) != ZERO_ADDRESS and init(self) ==> option_program(gvOptionToken30(self)) == self
# inter contract invariant: gvOptionToken20(self) != ZERO_ADDRESS and init(self) ==> option_program(gvOptionToken20(self)) == self
# inter contract invariant: gvOptionToken10(self) != ZERO_ADDRESS and init(self) ==> option_program(gvOptionToken10(self)) == self

#@ always ensures: msg.sender != self ==> storage(msg.sender) == old(storage(msg.sender))
#@ always ensures: success() ==> forall({a: address},
    #@ a != self
    #@ and a != gvOptionToken30(self)
    # and a != gvOptionToken20(self)
    # and a != gvOptionToken10(self)
    #@ ==> storage(a) == old(storage(a)))


#@ ensures: gvToken != self ==> storage(gvToken) == old(storage(gvToken))
@public
@nonreentrant("setup")
def setup(_gvAgent: address, _team: address, token: address, gvToken: address):
    raise "Not implemented"


#@ ensures: success() ==> result() == ico(self)
@public
@constant
def ico() -> address:
    raise "Not implemented"


#@ ensures: success() ==> result() == gvOptionToken30(self)
@public
@constant
def gvOptionToken30() -> address:
    raise "Not implemented"


#@ ensures: success() ==> result() == gvOptionToken20(self)
@public
@constant
def gvOptionToken20() -> address:
    raise "Not implemented"


#@ ensures: success() ==> result() == gvOptionToken10(self)
@public
@constant
def gvOptionToken10() -> address:
    raise "Not implemented"


@public
@constant
def getBalance() -> (uint256, uint256, uint256):
    raise "Not implemented"


#@ performs: destroy[GVOT.token[gvOptionToken30(self)]](min(balanceOf(gvOptionToken30(self))[buyer], usdCents * token30perCent), actor=buyer)
#@ ensures: success() ==> result() == old(tuple(min(balanceOf(gvOptionToken30(self))[buyer], usdCents * token30perCent),  # executedTokens
    #@ usdCents - (min(balanceOf(gvOptionToken30(self))[buyer], usdCents * token30perCent) / token30perCent)))  # remainingCents
#@ ensures: old(gvOptionToken30(self)) == ZERO_ADDRESS ==> revert()
@public
def executeOptions(buyer: address, usdCents: uint256, txHash: string[32]) -> (uint256, uint256):
    raise "Not implemented"


#@ performs: create[GVOT.token[gvOptionToken30(self)]](
    #@ (usdCents * option30perCent if remaining_tokens(gvOptionToken30(self)) >= usdCents * option30perCent else
    #@ remaining_tokens(gvOptionToken30(self))) if remaining_tokens(gvOptionToken30(self)) > 0 else 0,
    #@ to=buyer, actor=self)
#@ ensures: old(gvOptionToken30(self)) == ZERO_ADDRESS ==> revert()
@public
def buyOptions(buyer: address, usdCents: uint256, txHash: string[32]):
    raise "Not implemented"
