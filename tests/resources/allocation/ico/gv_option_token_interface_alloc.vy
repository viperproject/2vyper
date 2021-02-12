#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

#@ interface

#@ ghost:
    #@ def option_program() -> address: ...
    #@ def token_limit() -> uint256: ...
    #@ def remaining_tokens() -> uint256: ...
    #@ def balanceOf() -> map(address, uint256): ...
    #@ def minter() -> address: ...
    #@ def total_supply() -> uint256: ...
    #@ def allowances() -> map(address, map(address, uint256)): ...

#@ resource: token()


#@ invariant: option_program(self) == old(option_program(self))
#@ invariant: total_supply(self) == sum(balanceOf(self))

#@ invariant: old(token_limit(self)) != 0 ==> token_limit(self) == old(token_limit(self))

#@ invariant: remaining_tokens(self) == token_limit(self) - total_supply(self)

#@ invariant: allocated[token]() == balanceOf(self)
#@ invariant: forall({a: address}, {allocated[creator(token)](a)}, allocated[creator(token)](a) == (1 if a == minter(self) else 0))

#@ invariant: forall({o: address, s: address}, allowances(self)[o][s] == offered[token <-> token](1, 0, o, s))
#@ invariant: forall({a: address}, trusted(option_program(self), by=a))

#@ always ensures: forall({a: address}, a != self ==> storage(a) == old(storage(a)))

#@ ensures: success() ==> result() == option_program(self)
@public
@constant
def option_program() -> address:
    raise "Not implemented"


#@ ensures: msg.sender != option_program(self) ==> revert()
@public
def setup(_name: string[64], _symbol: string[32], _TOKEN_LIMIT: uint256):
    raise "Not implemented"


#@ ensures: msg.sender != option_program(self) ==> revert()
#@ performs: create[token](value, to=buyer)
@public
def buyOptions(buyer: address, value: uint256):
    raise "Not implemented"


#@ ensures: success() ==> result() == remaining_tokens(self)
@public
@constant
def remainingTokensCount() -> uint256:
    raise "Not implemented"


#@ ensures: msg.sender != option_program(self) ==> revert()
#@ ensures: success() ==> result() == min(old(balanceOf(self))[addr], optionsCount)
#@ performs: destroy[token](min(balanceOf(self)[addr], optionsCount), actor=addr)
@public
def executeOption(addr: address, optionsCount: uint256) -> uint256:
    raise "Not implemented"


#@ ensures: success() ==> result() == total_supply(self)
@public
@constant
def totalSupply() -> uint256:
    raise "Not implemented"


#@ ensures: success() ==> result() == balanceOf(self)[a]
@public
@constant
def balanceOf(a: address) -> uint256:
    raise "Not implemented"


#@ ensures: success() ==> result() == allowances(self)[_owner][_spender]
@public
@constant
def allowance(_owner: address, _spender: address) -> uint256:
    raise "Not implemented"


#@ performs: reallocate[token](_value, to=_to)
@public
def transfer(_to: address, _value: uint256) -> bool:
    raise "Not implemented"


#@ performs: exchange[token <-> token](1, 0, _from, msg.sender, times=_value)
#@ performs: reallocate[token](_value, to=_to)
@public
def transferFrom(_from : address, _to: address, _value: uint256) -> bool:
    raise "Not implemented"


#@ performs: revoke[token <-> token](1, 0, to=_spender)
#@ performs: offer[token <-> token](1, 0, to=_spender, times=_value)
@public
def approve(_spender: address, _value : uint256) -> bool:
    raise "Not implemented"


@public
@constant
def name() -> string[64]:
    raise "Not implemented"

@public
@constant
def symbol() -> string[32]:
    raise "Not implemented"

@public
@constant
def decimals() -> uint256:
    raise "Not implemented"
