#:: IgnoreFile(silicon)(0)

#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

import tests.resources.allocation.ico.gvtoken_interface_alloc as GVT
import tests.resources.allocation.ico.gv_option_token_interface_alloc as GVOT
import tests.resources.allocation.ico.migration_agent_interface as MigrationAgent
import tests.resources.allocation.ico.simplified_gv_option_program_interface_alloc as GVOptionProgram

option30perCent: constant(uint256) = 26 * 10 ** 16 # GVOT30 tokens per usd cent during option purchase
option20perCent: constant(uint256) = 24 * 10 ** 16 # GVOT20 tokens per usd cent during option purchase
option10perCent: constant(uint256) = 22 * 10 ** 16 # GVOT10 tokens per usd cent during option purchase
token30perCent: constant(uint256)  = 13684210526315800  # GVT tokens per usd cent during execution of GVOT30
token20perCent: constant(uint256)  = 12631578947368500  # GVT tokens per usd cent during execution of GVOT20
token10perCent: constant(uint256)  = 11578947368421100  # GVT tokens per usd cent during execution of GVOT10

TOKEN_FOR_SALE: constant(uint256) = 33 * 10 ** 6 * 10 ** 18

_init: bool

gvAgent: address
team: address

gvToken: GVT
optionProgram: GVOptionProgram
teamAllocator: address
migrationMaster: address

tokenSold: uint256

state: uint256
isPaused: bool

#@ preserves:
    #@ always ensures: self._init ==> self.state != 4 ==> frozen(self.gvToken)
    #@ always ensures: locked("lock") and old(self.state) == 3 ==> self.state == old(self.state)

# Properties about gvToken and optionProgram
#@ invariant: self._init ==> self.gvToken != self and self.gvToken != ZERO_ADDRESS
#@ invariant: self._init and self.optionProgram != ZERO_ADDRESS ==> self.optionProgram != self and self.optionProgram != GVOptionProgram(self.gvToken)
#@ invariant: old(self._init) and old(self.optionProgram) != ZERO_ADDRESS ==> old(self.optionProgram) == self.optionProgram
#@ invariant: old(self._init) ==> old(self.gvToken) == self.gvToken
# Once we are initialized we stay initialized and if the contract is past creation, it is surely initialized.
#@ invariant: (old(self._init) ==> self._init) and (self.state > 0 ==> self._init)
#@ invariant: self.optionProgram == ZERO_ADDRESS ==> self.state == 0

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
#@ always ensures: old(self._init) ==> migration_agent(self.gvToken) == 0 and old(sum(allocated[GVT.token[self.gvToken]]())) > sum(allocated[GVT.token[self.gvToken]]()) ==> self.state == 3 or self.state == 2



@public
def __init__():
    pass


@public
def setup(token: address, _team: address, _gvAgent: address, _teamAllocator: address, _migrationMaster: address):
    assert self._init == False

    assert token != ZERO_ADDRESS

    self.gvToken = GVT(create_forwarder_to(token))
    assert self.gvToken != self

    self.teamAllocator = _teamAllocator
    self.migrationMaster = _migrationMaster
    self.team = _team
    self.gvAgent = _gvAgent
    self.state = 0
    self.isPaused = False

    assert self.gvToken.get_ico() == self
    assert self.gvToken.isFrozen()
    assert self.optionProgram == ZERO_ADDRESS
    self._init = True
    self.gvToken.setup(_migrationMaster)


@public
def initOptionProgram(token: address, option_program: address):
    assert self._init
    assert self.state == 0
    assert msg.sender == self.team

    assert option_program != ZERO_ADDRESS
    assert token != ZERO_ADDRESS

    if self.optionProgram == ZERO_ADDRESS:
        self.optionProgram = GVOptionProgram(create_forwarder_to(option_program))
        assert self.optionProgram != self
        assert self.optionProgram != GVOptionProgram(self.gvToken)
        assert self.optionProgram.ico() == self
        self.optionProgram.setup(self.gvAgent, self.team, token, self.gvToken)


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

#@ performs: create[GVT.token[self.gvToken]](11 * (GVT.total_supply(self.gvToken) * 4 / 3) / 100, actor=self, to=self.teamAllocator)
#@ performs: create[GVT.token[self.gvToken]](     (GVT.total_supply(self.gvToken) * 4 / 3) /  20, actor=self, to=_fund)
#@ performs: create[GVT.token[self.gvToken]]( 9 * (GVT.total_supply(self.gvToken) * 4 / 3) / 100, actor=self, to=_bounty)
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

@private
def buyTokensInternal(buyer: address, usdCents: uint256, txHash: string[32]) -> uint256:
    assert usdCents > 0

    tokens: uint256 = usdCents * 10 ** 16
    assert self.tokenSold + tokens <= TOKEN_FOR_SALE
    self.tokenSold += tokens

    self.gvToken.mint(buyer, tokens)
    return 0


#@ performs: create[GVT.token[self.gvToken]](usdCents * 10 ** 16, actor=self, to=buyer)
@nonreentrant("lock")
@public
def buyTokens(buyer: address, usdCents: uint256, txHash: string[32]) -> uint256:
    assert msg.sender == self.gvAgent
    assert self.state == 3
    assert not self.isPaused
    return self.buyTokensInternal(buyer, usdCents, txHash)


#@ performs: destroy[GVOT.token[gvOptionToken30(self.optionProgram)]](min(GVOT.balanceOf(gvOptionToken30(self.optionProgram))[buyer], usdCents * token30perCent), actor=buyer)
#@ performs: create[GVT.token[self.gvToken]](min(GVOT.balanceOf(gvOptionToken30(self.optionProgram))[buyer], usdCents * token30perCent), actor=self, to=buyer)
#@ performs: create[GVT.token[self.gvToken]]((usdCents - (min(GVOT.balanceOf(gvOptionToken30(self.optionProgram))[buyer], usdCents * token30perCent) / token30perCent)) * 10 ** 16 if self.state == 3 else 0, actor=self, to=buyer)
@nonreentrant("lock")
@public
def buyTokensByOptions(buyer: address, usdCents: uint256, txHash: string[32]) -> uint256:
    assert msg.sender == self.gvAgent
    assert not self.isPaused
    assert self.state == 3 or self.state == 2
    assert usdCents > 0

    executedTokens: uint256 = 0
    remainingCents: uint256 = 0
    executedTokens, remainingCents = self.optionProgram.executeOptions(buyer, usdCents, txHash)

    if executedTokens > 0:
        assert self.tokenSold + executedTokens <= TOKEN_FOR_SALE
        self.tokenSold += executedTokens

        self.gvToken.mint(buyer, executedTokens)

    if self.state == 3:
        return self.buyTokensInternal(buyer, remainingCents, txHash)
    else:
        return remainingCents


#@ performs: create[GVOT.token[gvOptionToken30(self.optionProgram)]](
    #@ (usdCents * option30perCent if remaining_tokens(gvOptionToken30(self.optionProgram)) >= usdCents * option30perCent else
    #@ remaining_tokens(gvOptionToken30(self.optionProgram))) if remaining_tokens(gvOptionToken30(self.optionProgram)) > 0 else 0,
    #@ to=buyer, actor=self.optionProgram)
@public
def buyOptions(buyer: address, usdCents: uint256, txHash: string[32]):
    assert msg.sender == self.gvAgent
    assert not self.isPaused
    assert self.state == 2

    self.optionProgram.buyOptions(buyer, usdCents, txHash)
