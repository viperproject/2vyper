#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

mp: map(int128, uint256)
f: uint256


#@ ensures: success() == (k <= old(self.f))
@public
def minus(k: uint256):
    self.f -= k


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.f + k == old(self.f)
@public
def minus_fail(k: uint256):
    self.f -= k


#@ ensures: success() == (self.f <= old(self.mp[12]))
@public
def map_minus():
    self.mp[12] -= self.f


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.mp[12] + self.f == old(self.mp[12])
@public
def map_minus_fail():
    self.mp[12] -= self.f


#@ ensures: success() == (a != 0)
@public
def _div(a: uint256):
    self.f /= a


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success()
@public
def div_fail(a: uint256):
    self.f /= a