#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import simple_increase

#@ config: trust_casts

token_A: simple_increase
token_B: simple_increase
_diff: uint256
_lock: bool
_init: bool

#@ preserves:
    #@ always ensures: old(self._lock) == self._lock
    #@ always ensures: old(self._init) == self._init
    #:: Label(ICP)
    #@ always ensures: self._lock ==> mapping(self.token_A)[self] == old(mapping(self.token_A)[self])
    #@ always ensures: self._lock ==> mapping(self.token_B)[self] == old(mapping(self.token_B)[self])

# These variables are constant
#@ invariant: self.token_A == old(self.token_A)
#@ invariant: self.token_B == old(self.token_B)

# Once initialized _diff does not change anymore
#@ invariant: old(self._init) ==> self._init and self._diff == old(self._diff)

# Invariant we want to prove
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


#:: ExpectedOutput(postcondition.violated:assertion.false, ICP)
@public
def increase() -> bool:
    assert self._init
    result: bool = False
    if self.token_A.get() != MAX_UINT256 and self.token_B.get() != MAX_UINT256:
        temp_lock: bool = self._lock
        self._lock = True
        self.token_A.increase()
        self.token_B.increase()
        self._lock = temp_lock
        result = True
    return result
