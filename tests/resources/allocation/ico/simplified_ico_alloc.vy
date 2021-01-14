#:: IgnoreFile(silicon)(0)

#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

import tests.resources.allocation.ico.gvtoken_interface_alloc as GVT

state: uint256
isPaused: bool
teamAllocator: address
gvToken: GVT
optionProgram: address
_init: bool

#@ preserves:
    #@ always ensures: self._init ==> self.state != 4 ==> frozen(self.gvToken)
    #@ always ensures: locked("lock") and old(self.state) == 3 ==> self.state == old(self.state)

# Properties about gvToken and optionProgram
#@ invariant: self.gvToken != self and self.gvToken != ZERO_ADDRESS
#@ invariant: self.optionProgram != self and self.optionProgram != self.gvToken and self.optionProgram != ZERO_ADDRESS
#@ invariant: old(self.optionProgram) == self.optionProgram and old(self.gvToken) == self.gvToken
# Once we are initialized we stay initialized and if the contract is past creation, it is surely initialized.
#@ invariant: (old(self._init) ==> self._init) and (self.state > 0 ==> self._init)

#@ inter contract invariant: self._init ==> gvtoken_ico(self.gvToken) == self and (self.state != 4 ==> frozen(self.gvToken))

# Property spec_01
#@ always ensures: old(self.state) == 0 ==> self.state == 0 or self.state == 1
# Property spec_02
#@ always ensures: old(self.state) == 1 ==> self.state == 1 or self.state == 2
# Property spec_03
#@ always ensures: old(self.state) == 2 ==> self.state == 2 or self.state == 3
# Property spec_04
#@ always ensures: old(self.state) == 3 ==> self.state == 3 or self.state == 4
# Property spec_05
#@ always ensures: old(self.state) == 4 ==> self.state == 4
# Property spec_06 (altered)
# Original property had not "self.state != 4", but this would not be true if we finishIco from a paused state.
#@ always ensures: self.isPaused and self.state != 4 ==> sum(allocated[GVT.token[self.gvToken]]()) == old(sum(allocated[GVT.token[self.gvToken]]()))
# Property spec_07 (altered)
#@ inter contract invariant: self._init ==> not frozen(self.gvToken) ==> self.state == 4
# Property spec_08
#@ always ensures: migration_agent(self.gvToken) == 0 and old(sum(allocated[GVT.token[self.gvToken]]())) > sum(allocated[GVT.token[self.gvToken]]()) ==> self.state == 3 or self.state == 2



@public
def __init__(token: address, op: address, ta: address):
    assert token != op
    assert token != self
    assert token != ZERO_ADDRESS
    assert op != self
    assert op != ZERO_ADDRESS

    self.gvToken = GVT(token)
    self.optionProgram = op

    self.teamAllocator = ta
    self.state = 0
    self.isPaused = False

    assert self.gvToken.isFrozen()
    assert self.gvToken.get_ico() == self
    self._init = True


@public
def startOptionsSelling():
    assert self._init
    assert self.state == 0
    assert self.optionProgram != ZERO_ADDRESS
    self.state = 1


@public
def startIcoForOptionsHolders():
    assert self.state == 1
    self.state = 2


@public
def startIco():
    assert self.state == 2
    self.state = 3


@public
def pauseIco():
    assert self.state == 1 or self.state == 2 or self.state == 3
    assert not self.isPaused
    self.isPaused = True


@public
def resumeIco():
    assert self.state == 1 or self.state == 2 or self.state == 3
    assert self.isPaused
    self.isPaused = False

#@ performs: create[GVT.token[self.gvToken]](11 * (total_supply(self.gvToken) * 4 / 3) / 100, actor=self, to=self.teamAllocator)
#@ performs: create[GVT.token[self.gvToken]](     (total_supply(self.gvToken) * 4 / 3) /  20, actor=self, to=_fund)
#@ performs: create[GVT.token[self.gvToken]]( 9 * (total_supply(self.gvToken) * 4 / 3) / 100, actor=self, to=_bounty)
@nonreentrant("lock")
@public
def finishIco(_fund: address, _bounty: address):
    assert self.state == 3
    self.state = 4
    mintedTokens: uint256 = self.gvToken.totalSupply()
    if mintedTokens > 0 :
        totalAmount: uint256 = mintedTokens * 4 / 3                    # 75% of total tokens are for sale, get 100%
        self.gvToken.mint(self.teamAllocator, 11 * totalAmount / 100)  # 11% for team to the time-locked wallet
        self.gvToken.mint(_fund, totalAmount / 20)                     # 5% for Genesis Vision fund
        self.gvToken.mint(_bounty, 9 * totalAmount / 100)              # 9% for Advisers, Marketing, Bounty
        self.gvToken.unfreeze()


#@ performs: create[GVT.token[self.gvToken]](value, actor=self, to=buyer)
@nonreentrant("lock")
@public
def buyTokens(buyer: address, value: uint256):
    assert self.state == 3
    assert not self.isPaused
    self.gvToken.mint(buyer, value)
