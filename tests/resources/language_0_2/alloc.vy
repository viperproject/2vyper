# @version 0.2.x

#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Interface for the used methods in ERC1363

#@ config: allocation, no_derived_wei_resource

#@ interface

#@ resource: token()

#@ ghost:
    #@ def balanceOf() -> HashMap[address, uint256]: ...
    #@ def minter() -> address: ...
    #@ def total_supply() -> uint256: ...
    #@ def allowances() -> HashMap[address, HashMap[address, uint256]]: ...

#@ invariant: minter(self) == old(minter(self))
#@ invariant: total_supply(self) == sum(balanceOf(self))

#@ invariant: allocated[token]() == balanceOf(self)
#@ invariant: forall({a: address}, {allocated[creator(token)](a)}, allocated[creator(token)](a) == (1 if a == minter(self) else 0))

#@ invariant: forall({o: address, s: address}, allowances(self)[o][s] == offered[token <-> token](1, 0, o, s))

# Automatically caller private (there should be no need to write that)
# caller private: conditional(forall({a: address}, not trusted(a, by=caller())), balanceOf(self)[caller()] - sum(allowance(self)[caller()]))
# caller private: conditional(forall({a: address}, not trusted(a, by=caller())) and sum(allowance(self)[caller()]) == 0, allowance(self)[caller()])

# Functions

#@ ensures: success() ==> result() == total_supply(self)
@view
@external
def totalSupply() -> uint256:
    raise "Not implemented"


#@ ensures: success() ==> result() == allowances(self)[_owner][_spender]
@view
@external
def allowance(_owner: address, _spender: address) -> uint256:
    raise "Not implemented"

#@ ensures: success() ==> result() == balanceOf(self)[a]
@view
@external
def balanceOf(a: address) -> uint256:
    raise "Not implemented"

#@ performs: reallocate[token](_value, to=_to)
@external
def transfer(_to: address, _value: uint256) -> bool:
    raise "Not implemented"

#@ performs: exchange[token <-> token](1, 0, _from, msg.sender, times=_value)
#@ performs: reallocate[token](_value, to=_to)
@external
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    raise "Not implemented"

#@ performs: revoke[token <-> token](1, 0, to=_spender)
#@ performs: offer[token <-> token](1, 0, to=_spender, times=_value)
@external
def approve(_spender: address, _value: uint256) -> bool:
    raise "Not implemented"

#@ performs: destroy[token](_value)
@external
def burn(_value: uint256):
    raise "Not implemented"

#@ performs: exchange[token <-> token](1, 0, _from, msg.sender, times=min(_value, balanceOf(self)[_from]))
#@ performs: destroy[token](_value)
@external
def burnFrom(_from: address, _value: uint256):
    raise "Not implemented"

#@ performs: create[token](_value, to=_to)
@external
def mint(_to: address, _value: uint256):
    raise "Not implemented"

#@ performs: reallocate[token](amount, to=recipient)
@external
def transferAndCall(recipient: address, amount: uint256, data: Bytes[1024]) -> bool:
    raise "Not implemented"

#@ performs: exchange[token <-> token](1, 0, sender, msg.sender, times=amount)
#@ performs: reallocate[token](amount, to=recipient)
@external
def transferFromAndCall(sender: address, recipient: address, amount: uint256, data: Bytes[1024]) -> bool:
    raise "Not implemented"

#@ performs: revoke[token <-> token](1, 0, to=spender)
#@ performs: offer[token <-> token](1, 0, to=spender, times=amount)
@external
def approveAndCall(spender: address, amount: uint256, data: Bytes[1024]) -> bool:
    raise "Not implemented"

@view
@external
def name() -> String[64]:
    raise "Not implemented"

@view
@external
def symbol() -> String[32]:
    raise "Not implemented"

@view
@external
def decimals() -> uint256:
    raise "Not implemented"