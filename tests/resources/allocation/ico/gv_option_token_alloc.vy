#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

from . import gv_option_token_interface_alloc

implements: gv_option_token_interface_alloc

option_program: public(address)

name: public(string[64])
symbol: public(string[32])
decimals: public(uint256)

TOKEN_LIMIT: uint256

total_supply: uint256
balances: map(address, uint256)
allowances: map(address, map(address, uint256))

#@ ghost:
    #@ @implements
    #@ def option_program() -> address: self.option_program
    #@ @implements
    #@ def token_limit() -> uint256: self.TOKEN_LIMIT
    #@ @implements
    #@ def balanceOf() -> map(address, uint256): self.balances
    #@ @implements
    #@ def minter() -> address: self.option_program
    #@ @implements
    #@ def total_supply() -> uint256: self.total_supply
    #@ @implements
    #@ def allowances() -> map(address, map(address, uint256)): self.allowances

@public
def __init__(a: address):
    assert a != ZERO_ADDRESS
    self.option_program = a

    #@ create[creator(token)](1, to=self.option_program)

    #@ foreach({a: address}, trust(self.option_program, True, actor=a))

    self.decimals = 18


@public
def setup(_name: string[64], _symbol: string[32], _TOKEN_LIMIT: uint256):
    assert msg.sender == self.option_program
    assert self.TOKEN_LIMIT == 0
    self.name = _name
    self.symbol = _symbol
    self.TOKEN_LIMIT = _TOKEN_LIMIT


@public
def buyOptions(buyer: address, value: uint256):
    assert msg.sender == self.option_program
    assert value > 0
    assert self.total_supply + value < self.TOKEN_LIMIT

    self.balances[buyer] += value
    #@ create[token](value, to=buyer)
    self.total_supply += value


@public
@constant
def remainingTokensCount() -> uint256:
    return self.TOKEN_LIMIT - self.total_supply


@public
def executeOption(addr: address, optionsCount: uint256) -> uint256:
    assert msg.sender == self.option_program
    options_count: uint256 = optionsCount
    if self.balances[addr] < options_count:
        options_count = self.balances[addr]

    if options_count == 0:
        return 0

    self.balances[addr] -= options_count
    #@ assert self.option_program == option_program(self), UNREACHABLE
    #@ destroy[token](options_count, actor=addr)
    self.total_supply -= options_count

    return options_count


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

    self.balances[msg.sender] -= _value
    #@ reallocate[token](_value, to=_to)
    self.balances[_to] += _value
    return True


@public
def transferFrom(_from : address, _to: address, _value: uint256) -> bool:
    self.balances[_from] -= _value
    self.balances[_to] += _value
    self.allowances[_from][msg.sender] -= _value
    #@ exchange[token <-> token](1, 0, _from, msg.sender, times=_value)
    #@ reallocate[token](_value, to=_to)
    return True


@public
def approve(_spender: address, _value : uint256) -> bool:
    #@ revoke[token <-> token](1, 0, to=_spender)
    self.allowances[msg.sender][_spender] = _value
    #@ offer[token <-> token](1, 0, to=_spender, times=_value)
    return True
