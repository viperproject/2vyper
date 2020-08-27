#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def gvtoken_totalSupply() -> uint256: ...
    #@ def frozen() -> bool: ...
    #@ def migration_agent() -> address: ...
    #@ def gvtoken_ico() -> address: ...

# Once unfrozen it cannot be frozen anymore
#@ invariant: not old(frozen(self)) ==> not frozen(self)
# ICO stays the same
#@ invariant: old(gvtoken_ico(self)) == gvtoken_ico(self)
# Total supply only increases (there is no burn)
#@ invariant: gvtoken_totalSupply(self) >= old(gvtoken_totalSupply(self))


#@ always ensures: msg.sender != self ==> storage(msg.sender) == old(storage(msg.sender))


#@ caller private: conditional(gvtoken_ico(self) == caller(), frozen(self))
#@ caller private: conditional(gvtoken_ico(self) == caller(), gvtoken_totalSupply(self))


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
#@ ensures: success() ==> gvtoken_totalSupply(self) == old(gvtoken_totalSupply(self))
@public
def unfreeze():
    raise "Not implemented"


#@ ensures: msg.sender != gvtoken_ico(self) ==> revert()
#@ ensures: success() ==> old(frozen(self)) == frozen(self)
#@ ensures: success() ==> gvtoken_totalSupply(self) == old(gvtoken_totalSupply(self)) + value
@public
def mint(holder: address, value: uint256):
    raise "Not implemented"


#@ ensures: success() ==> result() == gvtoken_totalSupply(self)
@public
@constant
def totalSupply() -> uint256:
    raise "Not implemented"

