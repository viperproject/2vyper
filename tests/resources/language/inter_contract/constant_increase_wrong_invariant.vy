#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import simple_increase

#@ config: trust_casts

token_A: simple_increase
_value: uint256
_init: bool

#@ preserves:
    #@ always ensures: old(self._init) == self._init

# These variables are constant
#@ invariant: self.token_A == old(self.token_A)

# Once initialized _value does not change anymore
#@ invariant: old(self._init) ==> self._init and self._value == old(self._value)

# Properties about some variables
#@ invariant: self.token_A != self and self.token_A != ZERO_ADDRESS

# Invariant we want to prove
#:: Label(INV)
#@ inter contract invariant: self._init ==> self._value >= mapping(self.token_A)[self]


@public
def __init__(token_A_address: address , token_B_address: address):
    assert token_A_address != self and token_A_address != ZERO_ADDRESS
    self.token_A = simple_increase(token_A_address)
    value_A: uint256 = self.token_A.get()
    self._value = value_A
    self._init = True


@public
def increase() -> bool:
    assert self._init
    result: bool = False
    if self.token_A.get() != MAX_UINT256:
        #:: ExpectedOutput(after.call.invariant:assertion.false, INV)
        self.token_A.increase()
        result = True
    return result
