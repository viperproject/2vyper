#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

from . import gvtoken_interface_alloc
import tests.resources.allocation.ico.migration_agent_interface as MigrationAgent

implements: gvtoken_interface_alloc

TOKEN_LIMIT: constant(uint256) = 44 * 10 ** 6 * 10 ** 18
total_supply: uint256
balances: map(address, uint256)
allowances: map(address, map(address, uint256))
frozen: public(bool)

migration_master: public(address)
migration_agent: public(MigrationAgent)
total_migrated: public(uint256)

ico: public(address)

name: public(string[64])
symbol: public(string[32])
decimals: public(uint256)

#@ ghost:
    #@ @implements
    #@ def frozen() -> bool: self.frozen
    #@ @implements
    #@ def migration_agent() -> address: self.migration_agent
    #@ @implements
    #@ def gvtoken_ico() -> address: self.ico
    #@ @implements
    #@ def balanceOf() -> map(address, uint256): self.balances
    #@ @implements
    #@ def minter() -> address: self.ico
    #@ @implements
    #@ def total_supply() -> uint256: self.total_supply
    #@ @implements
    #@ def allowances() -> map(address, map(address, uint256)): self.allowances


@public
def __init__(a: address):
    assert a != ZERO_ADDRESS
    self.ico = a
    self.frozen = True

    #@ create[creator(token)](1, to=self.ico)

    self.name = "Genesis Vision Token"
    self.symbol = "GVT"
    self.decimals = 18

@public
def setup(migrationMaster: address):
    assert self.frozen
    assert self.migration_master == ZERO_ADDRESS
    assert migrationMaster != ZERO_ADDRESS

    self.migration_master = migrationMaster


@public
def mint(holder: address, value: uint256):
    assert msg.sender == self.ico
    assert value > 0
    assert self.total_supply + value <= TOKEN_LIMIT

    self.balances[holder] += value
    #@ create[token](value, to=holder)
    self.total_supply += value

@public
def unfreeze():
    assert msg.sender == self.ico
    self.frozen = False

@public
@constant
def isFrozen() -> bool:
    return self.frozen

@public
@constant
def get_ico() -> address:
    return self.ico

@public
@constant
def totalSupply() -> uint256:
    return self.total_supply

@public
@constant
def balanceOf(a: address) -> uint256:
    return self.balances[a]


@public
@constant
def allowance(_owner: address, _spender: address) -> uint256:
    return self.allowances[_owner][_spender]

@public
def transfer(_to: address, _value: uint256) -> bool:
    assert _to != ZERO_ADDRESS
    assert not self.frozen

    self.balances[msg.sender] -= _value
    #@ reallocate[token](_value, to=_to)
    self.balances[_to] += _value
    return True


@public
def transferFrom(_from : address, _to: address, _value: uint256) -> bool:
    assert not self.frozen

    self.balances[_from] -= _value
    self.balances[_to] += _value
    self.allowances[_from][msg.sender] -= _value
    #@ exchange[token <-> token](1, 0, _from, msg.sender, times=_value)
    #@ reallocate[token](_value, to=_to)
    return True

@public
def approve(_spender: address, _value : uint256) -> bool:
    assert not self.frozen

    #@ revoke[token <-> token](1, 0, to=_spender)
    self.allowances[msg.sender][_spender] = _value
    #@ offer[token <-> token](1, 0, to=_spender, times=_value)
    return True


@public
def migrate(value: uint256):
    assert self.migration_agent != ZERO_ADDRESS
    assert value > 0

    self.balances[msg.sender] -= value
    #@ destroy[token](value)
    self.total_supply -= value
    self.total_migrated += value
    self.migration_agent.migrateFrom(msg.sender, value)


@public
def setMigrationAgent(_agent: address):
    assert self.migration_agent == ZERO_ADDRESS
    assert msg.sender == self.migration_master
    self.migration_agent = MigrationAgent(_agent)


@public
def setMigrationMaster(_master: address):
    assert msg.sender == self.migration_master
    assert _master != ZERO_ADDRESS
    self.migration_master = _master

