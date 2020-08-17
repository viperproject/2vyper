#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import gvtoken_interface

implements: gvtoken_interface

TOKEN_LIMIT: constant(uint256) = 44 * 10 ** 6 * 10 ** 18
total_supply: uint256
balances: map(address, uint256)
frozen: bool
migration_agent: address
ico: address

#@ ghost:
    #@ @implements
    #@ def gvtoken_totalSupply() -> uint256: self.total_supply
    #@ @implements
    #@ def frozen() -> bool: self.frozen
    #@ @implements
    #@ def migration_agent() -> address: self.migration_agent
    #@ @implements
    #@ def gvtoken_ico() -> address: self.ico


@public
def __init__(ma: address, a: address):
    self.migration_agent = ma
    self.ico = a
    self.frozen = True


@public
@constant
def get_ico() -> address:
    return self.ico


@public
@constant
def isFrozen() -> bool:
    return self.frozen


@public
def unfreeze():
    assert msg.sender == self.ico
    self.frozen = False


@public
def mint(holder: address, value: uint256):
    assert msg.sender == self.ico
    assert value > 0
    assert self.total_supply + value <= TOKEN_LIMIT

    self.balances[holder] += value
    self.total_supply += value


@public
@constant
def totalSupply() -> uint256:
    return self.total_supply

