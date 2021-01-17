#:: IgnoreFile(silicon)(0)

#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

import tests.resources.allocation.ico.gv_option_token_interface_alloc as GVOT

from . import simplified_gv_option_program_interface_alloc

implements: simplified_gv_option_program_interface_alloc


option30perCent: constant(uint256) = 26 * 10 ** 16 # GVOT30 tokens per usd cent during option purchase
option20perCent: constant(uint256) = 24 * 10 ** 16 # GVOT20 tokens per usd cent during option purchase
option10perCent: constant(uint256) = 22 * 10 ** 16 # GVOT10 tokens per usd cent during option purchase
token30perCent: constant(uint256)  = 13684210526315800  # GVT tokens per usd cent during execution of GVOT30
token20perCent: constant(uint256)  = 12631578947368500  # GVT tokens per usd cent during execution of GVOT20
token10perCent: constant(uint256)  = 11578947368421100  # GVT tokens per usd cent during execution of GVOT10

gvAgent: public(address)
team: public(address)
ico: public(address)

gvOptionToken30: public(GVOT)
gvOptionToken20: public(GVOT)
gvOptionToken10: public(GVOT)

#@ ghost:
    #@ @implements
    #@ def gvOptionToken30() -> GVOT: self.gvOptionToken30
    #@ @implements
    #@ def gvOptionToken20() -> GVOT: self.gvOptionToken20
    #@ @implements
    #@ def gvOptionToken10() -> GVOT: self.gvOptionToken10
    #@ @implements
    #@ def ico() -> address: self.ico

@public
def __init__(_ico: address):
    assert _ico != ZERO_ADDRESS

    self.ico = _ico


@public
@nonreentrant("setup")
def setup(_gvAgent: address, _team: address, token: address):
    assert self.gvAgent == ZERO_ADDRESS
    assert self.team == ZERO_ADDRESS

    self.gvAgent = _gvAgent
    self.team = _team

    assert self.gvOptionToken30 == ZERO_ADDRESS
    self.gvOptionToken30 = GVOT(create_forwarder_to(token))
    assert self.gvOptionToken30.option_program() == self
    self.gvOptionToken30.setup("30% GVOT", "GVOT30", 26 * 10 ** 5 * 10 ** 18)

    assert self.gvOptionToken20 == ZERO_ADDRESS
    self.gvOptionToken20 = GVOT(create_forwarder_to(token))
    assert self.gvOptionToken20.option_program() == self
    self.gvOptionToken20.setup("20% GVOT", "GVOT20", 36 * 10 ** 5 * 10 ** 18)

    assert self.gvOptionToken10 == ZERO_ADDRESS
    self.gvOptionToken10 = GVOT(create_forwarder_to(token))
    assert self.gvOptionToken10.option_program() == self
    self.gvOptionToken10.setup("10% GVOT", "GVOT10", 55 * 10 ** 5 * 10 ** 18)


@public
@constant
def getBalance() -> (uint256, uint256, uint256):
    return (self.gvOptionToken30.remainingTokensCount(),
            self.gvOptionToken20.remainingTokensCount(),
            self.gvOptionToken10.remainingTokensCount())


@private
def executeIfAvailable(buyer: address, usdCents: uint256, txHash: string[32],
                       optionToken: address, optionType: uint256, optionPerCent: uint256) -> (uint256, uint256):
    optionsAmount: uint256 = usdCents * optionPerCent
    executedTokens: uint256 = GVOT(optionToken).executeOption(buyer, optionsAmount)
    remainingCents: uint256 = usdCents - (executedTokens / optionPerCent)
    return executedTokens, remainingCents


@public
def executeOptions(buyer: address, usdCents: uint256, txHash: string[32]) -> (uint256, uint256):
    assert msg.sender == self.ico
    assert usdCents > 0

    executedTokens: uint256 = 0
    remainingCents: uint256 = 0
    executedTokens, remainingCents = self.executeIfAvailable(buyer, usdCents, txHash, self.gvOptionToken30, 0, token30perCent)
    # if remainingCents == 0:
    #     return executedTokens, 0

    executed20: uint256 = 0
    # executed20, remainingCents = self.executeIfAvailable(buyer, usdCents, txHash, self.gvOptionToken20, 1, token20perCent)
    # if remainingCents == 0:
    #     return executedTokens + executed20, 0

    executed10: uint256 = 0
    # executed10, remainingCents = self.executeIfAvailable(buyer, usdCents, txHash, self.gvOptionToken10, 2, token10perCent)
    return executedTokens + executed20 + executed10, remainingCents


@private
def buyIfAvailable(buyer: address, usdCents: uint256, txHash: string[32],
                   optionToken: address, optionType: uint256, optionsPerCent: uint256) -> uint256:

    availableTokens: uint256 = GVOT(optionToken).remainingTokensCount()
    if availableTokens > 0:
        tokens: uint256 = usdCents * optionsPerCent
        if availableTokens >= tokens:
            GVOT(optionToken).buyOptions(buyer, tokens)
            return 0
        else:
            GVOT(optionToken).buyOptions(buyer, availableTokens)
            return usdCents - availableTokens / optionsPerCent

    return usdCents


@public
def buyOptions(buyer: address, usdCents: uint256, txHash: string[32]):
    assert msg.sender == self.ico
    assert usdCents > 0

    remainingCents: uint256 = self.buyIfAvailable(buyer, usdCents, txHash, self.gvOptionToken30, 0, option30perCent)
    # if remainingCents == 0:
    #     return

    # remainingCents = self.buyIfAvailable(buyer, usdCents, txHash, self.gvOptionToken20, 1, option20perCent)
    # if remainingCents == 0:
    #     return

    # remainingCents = self.buyIfAvailable(buyer, usdCents, txHash, self.gvOptionToken10, 2, option10perCent)
