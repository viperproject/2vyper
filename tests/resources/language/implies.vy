#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

f1: int128
f2: int128

#@ invariant: self.f1 == self.f2


#@ ensures: implies(success(), result() == 2 * self.f1)
@public
def add() -> int128:
    assert self.f1 > 10
    return self.f1 + self.f2


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() == self.f1 * self.f1)
@public
def mul() -> int128:
    assert self.f1 > 10
    return self.f1 + self.f2