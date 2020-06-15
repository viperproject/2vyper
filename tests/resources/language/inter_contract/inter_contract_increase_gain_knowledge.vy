#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import simple_increase_gain_knowledge

#@ config: trust_casts

token_A: simple_increase_gain_knowledge
token_B: simple_increase_gain_knowledge
_diff: uint256
_lock: bool
_init: bool

#@ preserves:
    #@ always ensures: old(self._lock) == self._lock
    #@ always ensures: old(self._init) == self._init

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
    self.token_A = simple_increase_gain_knowledge(token_A_address)
    self.token_B = simple_increase_gain_knowledge(token_B_address)
    value_A: uint256 = self.token_A.get()
    value_B: uint256 = self.token_B.get()
    assert(value_A >= value_B)
    self._diff = value_A - value_B
    self._lock = False
    self._init = True


#@ ensures: success() and result() ==> self != 0x000000001000000000010000000000000600000a
#@ ensures: result and self == 0x000000001000000000010000000000000600000a ==> failed(self.token_A)
@public
def increase() -> bool:
    result: bool = False
    assert not self._lock
    assert self._init
    if self.token_A.get() != MAX_UINT256 and self.token_B.get() != MAX_UINT256:
        result = True
        self._lock = True
        self.token_A.increase()
        self.token_B.increase()
        self._lock = False
    return result
