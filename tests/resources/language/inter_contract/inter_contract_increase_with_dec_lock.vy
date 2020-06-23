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
_init: bool

#@ preserves:
    #@ always ensures: old(self._init) == self._init
    #@ always ensures: locked("lock") ==> mapping(self.token_A)[self] == old(mapping(self.token_A)[self])
    #@ always ensures: locked("lock") ==> mapping(self.token_B)[self] == old(mapping(self.token_B)[self])

# These variables are constant
#@ invariant: self.token_A == old(self.token_A)
#@ invariant: self.token_B == old(self.token_B)

# Once initialized _diff does not change anymore
#@ invariant: old(self._init) ==> self._init and self._diff == old(self._diff)

# Invariant we want to prove
#@ inter contract invariant: not locked("lock") and self._init ==> self._diff == mapping(self.token_A)[self] - mapping(self.token_B)[self]

@public
def __init__(token_A_address: address , token_B_address: address):
    self.token_A = simple_increase(token_A_address)
    self.token_B = simple_increase(token_B_address)
    value_A: uint256 = self.token_A.get()
    value_B: uint256 = self.token_B.get()
    assert(value_A >= value_B)
    self._diff = value_A - value_B
    self._init = True


@nonreentrant("lock2")
@private
def foo():
    pass


@nonreentrant("lock")
@public
def increase() -> bool:
    assert self._init
    self.foo()
    result: bool = False
    if self.token_A.get() != MAX_UINT256 and self.token_B.get() != MAX_UINT256:
        self.token_A.increase()
        self.token_B.increase()
        result = True
    return result

