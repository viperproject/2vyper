#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import simple_increase_without_caller_private

#@ config: trust_casts

token_A: simple_increase_without_caller_private
_value: uint256
_init: bool

#@ preserves:
    #@ always ensures: old(self._init) == self._init
    #@ always ensures: old(mapping(self.token_A)[self]) <= mapping(self.token_A)[self]

# These variables are constant
#@ invariant: self.token_A == old(self.token_A)
#@ invariant: self._value == old(self._value)

# Invariant we want to prove
#:: Label(INV)
#@ inter contract invariant: self._init ==> self._value <= mapping(self.token_A)[self]

#@ requires: self._init
#@ requires: self._value == public_old(self._value)
#@ requires: self.token_A == public_old(self.token_A)
#@ requires: self._value <= mapping(self.token_A)[self]
@private
def increase() -> bool:
    result: bool = False
    if self.token_A.get() != MAX_UINT256:
        #:: ExpectedOutput(during.call.invariant:assertion.false, INV)
        self.token_A.increase()
        result = True
    return result
