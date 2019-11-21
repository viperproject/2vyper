#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from tests.resources.language.interfaces import interface

implements: interface


mp: map(int128, int128)


#:: Label(ZERO)
#@ invariant: forall({i: int128}, {self.mp[i]}, self.mp[i] == 0)

#@ ghost:
    #@ @implements
    #@ def _mapval(j: int128) -> int128: self.mp[j]


@public
def foo(i: int128) -> int128:
    assert i > 0
    return i


#:: ExpectedOutput(postcondition.not.implemented:assertion.false)
@public
def bar(u: uint256) -> uint256:
    return u + 1


@public
def get_val(j: int128) -> int128:
    return self.mp[j]


#:: ExpectedOutput(postcondition.not.implemented:assertion.false) | ExpectedOutput(carbon)(invariant.violated:assertion.false, ZERO)
@public
def set_val(j: int128, k: int128):
    self.mp[j] = k
