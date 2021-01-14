#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

#@ interface

#@ resource: token()

#@ ghost:
    #@ def frozen() -> bool: ...
    #@ def migration_agent() -> address: ...
    #@ def gvtoken_ico() -> address: ...
    #@ def balanceOf() -> map(address, uint256): ...
    #@ def minter() -> address: ...
    #@ def total_supply() -> uint256: ...
    #@ def allowances() -> map(address, map(address, uint256)): ...

# Once unfrozen it cannot be frozen anymore
#@ invariant: not old(frozen(self)) ==> not frozen(self)
# ICO stays the same
#@ invariant: old(gvtoken_ico(self)) == gvtoken_ico(self)
# Total supply only increases (there is no burn)
#@ invariant: total_supply(self) >= old(total_supply(self))

#@ invariant: minter(self) == old(minter(self))
#@ invariant: total_supply(self) == sum(balanceOf(self))

#@ invariant: allocated[token]() == balanceOf(self)
#@ invariant: forall({a: address}, {allocated[creator(token)](a)}, allocated[creator(token)](a) == (1 if a == minter(self) else 0))

#@ invariant: forall({o: address, s: address}, allowances(self)[o][s] == offered[token <-> token](1, 0, o, s))


#@ always ensures: msg.sender != self ==> storage(msg.sender) == old(storage(msg.sender))


#@ caller private: conditional(gvtoken_ico(self) == caller(), frozen(self))
#@ caller private: conditional(gvtoken_ico(self) == caller(), total_supply(self))


#@ ensures: success() ==> result() == gvtoken_ico(self)
@public
@constant
def get_ico() -> address:
    raise "Not implemented"


#@ ensures: success() ==> result() == frozen(self)
@public
@constant
def isFrozen() -> bool:
    raise "Not implemented"


#@ ensures: msg.sender != gvtoken_ico(self) ==> revert()
#@ ensures: success() ==> frozen(self) == False
@public
def unfreeze():
    raise "Not implemented"


#@ ensures: msg.sender != gvtoken_ico(self) ==> revert()
#@ ensures: success() ==> old(frozen(self)) == frozen(self)
#@ performs: create[token](value, to=holder)
@public
def mint(holder: address, value: uint256):
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


@constant
@public
def name() -> string[64]:
    raise "Not implemented"


@constant
@public
def symbol() -> string[32]:
    raise "Not implemented"


@constant
@public
def decimals() -> uint256:
    raise "Not implemented"

