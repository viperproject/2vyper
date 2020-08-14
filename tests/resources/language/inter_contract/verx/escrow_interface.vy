#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def deposits() -> map(address, uint256): ...
    #@ def refund_state() -> bool: ...
    #@ def success_state() -> bool: ...
    #@ def open_state() -> bool: ...
    #@ def owner() -> address: ...


# Simulated enum from Solidity "enum State {OPEN, SUCCESS, REFUND}"
#@ invariant: open_state(self) or success_state(self) or refund_state(self)
#@ invariant: open_state(self) ==> not success_state(self) and not refund_state(self)
#@ invariant: success_state(self) ==> not open_state(self) and not refund_state(self)
#@ invariant: refund_state(self) ==> not open_state(self) and not success_state(self)

# The owner stays the same
#@ invariant: owner(self) == old(owner(self))
# Once we are in the refund state, we cannot get out of it
#@ invariant: old(refund_state(self)) ==> refund_state(self)
# Once we are in the success state, we cannot get out of it
#@ invariant: old(success_state(self)) ==> success_state(self)
# If we do not refund, the deposit can not get withdrawn
#@ invariant: not refund_state(self) ==> sum(deposits(self)) >= old(sum(deposits(self)))

# Escrow does not modify the state of the caller
# always ensures: msg.sender != self ==> open_state(self) ==> storage(msg.sender) == old(storage(msg.sender))

# The simulated enum is only modifiable by owner
#@ caller private: conditional(owner(self) == caller(), success_state(self))
#@ caller private: conditional(owner(self) == caller(), refund_state(self))
#@ caller private: conditional(owner(self) == caller(), open_state(self))

#@ ensures: success() ==> result() == owner(self)
@public
@constant
def get_owner() -> address:
    raise "Not implemented"

#@ ensures: success() ==> result() == open_state(self)
@public
@constant
def is_open() -> bool:
    raise "Not implemented"


#@ ensures: success() ==> result() == success_state(self)
@public
@constant
def is_success() -> bool:
    raise "Not implemented"


#@ ensures: success() ==> result() == refund_state(self)
@public
@constant
def is_refund() -> bool:
    raise "Not implemented"


#@ ensures: old(open_state(self)) == open_state(self)
#@ ensures: success() ==> deposits(self)[p] == old(deposits(self)[p]) + msg.value
#@ ensures: success() ==> sum(deposits(self)) == old(sum(deposits(self))) + msg.value
@public
@payable
def deposit(p: address):
    raise "Not implemented"


#@ ensures: success() ==> old(success_state(self))
@public
def withdraw():
    raise "Not implemented"


#@ ensures: success() ==> old(refund_state(self))
@public
def claimRefund(p: address):
    raise "Not implemented"


#@ ensures: msg.sender != owner(self) ==> revert()
#@ ensures: success() ==> success_state(self) == True
#@ ensures: success() ==> sum(deposits(self)) == old(sum(deposits(self)))
@public
def close():
    raise "Not implemented"


#@ ensures: msg.sender != owner(self) ==> revert()
#@ ensures: success() ==> refund_state(self) == True
#@ ensures: success() ==> sum(deposits(self)) == old(sum(deposits(self)))
@public
def refund():
    raise "Not implemented"
