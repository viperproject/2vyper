#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


struct S:
    val: int128
    flag: bool


mp: map(int128, int128)
s: S


#@ ensures: success() ==> independent(self.mp, b)
@public
def do_nothing(b: bool):
    if b:
        self.mp[0] = self.mp[0]
    else:
        self.mp[1] = self.mp[1]


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success() ==> independent(self.mp, b)
@public
def do_nothing_fail(b: bool):
    if b:
        self.mp[0] = self.mp[1]
    else:
        self.mp[1] = self.mp[1]


#@ ensures: success() ==> independent(self.s, i)
@public
def assign_four(i: int128):
    if i % 2 == 0:
        self.s.val = 4
    else:
        self.s.val = 4


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success() ==> independent(self.s, i)
@public
def assign_four_fail(i: int128):
    if i % 2 == 0:
        self.s.val = 4
    else:
        self.s.val = 2
