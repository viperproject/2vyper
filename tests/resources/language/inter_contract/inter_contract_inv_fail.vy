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
_init: bool

#@ preserves:
    #@ always ensures: old(self._lock) == self._lock
    #@ always ensures: old(self._init) == self._init
    #@ always ensures: self._lock ==> mapping(self.token_A)[self] == old(mapping(self.token_A)[self])
    #@ always ensures: self._lock ==> mapping(self.token_B)[self] == old(mapping(self.token_B)[self])

# These variables are constant
#@ invariant: self.token_A == old(self.token_A)
#@ invariant: self.token_B == old(self.token_B)

# Once initialized _diff does not change anymore
#@ invariant: old(self._init) ==> self._init and self._diff == old(self._diff)

# Invariant we want to prove
#:: Label(INV)
#@ inter contract invariant: not self._lock and self._init ==> self._diff == mapping(self.token_A)[self] - mapping(self.token_B)[self]


@public
def __init__(token_A_address: address , token_B_address: address):
    self._lock = True
    self.token_A = simple_increase(token_A_address)
    self.token_B = simple_increase(token_B_address)
    value_A: uint256 = self.token_A.get()
    value_B: uint256 = self.token_B.get()
    assert(value_A >= value_B)
    self._diff = value_A - value_B
    self._lock = False
    self._init = True

#@ requires: self._init
#@ requires: not self._lock
#@ requires: self.token_A == public_old(self.token_A)
#@ requires: self.token_B == public_old(self.token_B)
#@ requires: self._diff == public_old(self._diff)
#@ requires: self._diff == mapping(self.token_A)[self] - mapping(self.token_B)[self]
#:: ExpectedOutput(carbon)(postcondition.violated:assertion.false)
#@ ensures: revert()
@private
def fail():
    #:: ExpectedOutput(during.call.invariant:assertion.false, INV) | ExpectedOutput(carbon)(after.call.invariant:assertion.false, INV)
    self.token_A.increase()
    #:: ExpectedOutput(carbon)(during.call.invariant:assertion.false, INV) | ExpectedOutput(carbon)(after.call.invariant:assertion.false, INV)
    self.token_B.increase()
