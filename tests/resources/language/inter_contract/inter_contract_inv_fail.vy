#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import simple_increase

#@ config: trust_casts, no_gas

token_A: simple_increase
token_B: simple_increase
_diff: uint256
_lock: bool

# These variables are constant
#@ invariant: self.token_A == old(self.token_A)
#@ invariant: self.token_B == old(self.token_B)

# Properties about some variables
#@ invariant: self.token_A != self and self.token_A != ZERO_ADDRESS
#@ invariant: self.token_B != self and self.token_B != ZERO_ADDRESS
#@ invariant: self.token_A != self.token_B
#@ invariant: not old(self._lock) ==> not self._lock

# Invariant we want to prove
#:: Label(INV)
#@ invariant: not self._lock ==> self._diff == mapping(self.token_A)[self] - mapping(self.token_B)[self]


@public
def __init__(token_A_address: address , token_B_address: address):
    self._lock = True
    assert token_A_address != self and token_A_address != ZERO_ADDRESS
    assert token_B_address != self and token_B_address != ZERO_ADDRESS
    assert token_A_address != token_B_address
    self.token_A = simple_increase(token_A_address)
    self.token_B = simple_increase(token_B_address)
    value_A: uint256 = self.token_A.get()
    value_B: uint256 = self.token_B.get()
    assert(value_A >= value_B)
    self._diff = value_A - value_B

#@ requires: not self._lock
#@ requires: self.token_A == public_old(self.token_A)
#@ requires: self.token_B == public_old(self.token_B)
#@ requires: self._diff == mapping(self.token_A)[self] - mapping(self.token_B)[self]
#@ ensures: success() ==> self.token_A == self.token_B
#@ ensures: success() ==> self.token_A != self.token_B
@private
def fail():
    #:: ExpectedOutput(call.invariant:assertion.false, INV)
    self.token_A.increase()
    self.token_B.increase()
