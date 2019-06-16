#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

f1: int128
f2: int128
f3: bool
f4: uint256

#:: Label(F1_F2)
#@ invariant: self.f1 == self.f2
#@ invariant: self.f3


@public
def __init__():
    self.f1 = 4
    self.f2 = self.f1
    self.f3 = not False

@public
def foo():
    l1: int128 = self.f1

#:: ExpectedOutput(invariant.violated:assertion.false, F1_F2)
@public
def bar():
    self.f1 = 5