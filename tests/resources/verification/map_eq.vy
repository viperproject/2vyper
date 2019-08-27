#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


mp: map(int128, int128)


#@ ensures: self.mp == old(self.mp)
@public
def no_change():
    pass


#@ ensures: self.mp == old(self.mp)
@public
def no_effective_change():
    self.mp[5] = self.mp[5]


#@ ensures: self.mp == old(self.mp)
@public
def no_effective_changes():
    old_mp: int128 = self.mp[4]
    self.mp[4] = 6
    self.mp[4] = 12
    self.mp[4] = old_mp


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.mp == old(self.mp)
@public
def changes():
    old_mp: int128 = self.mp[4]
    self.mp[4] = 6
    self.mp[4] = 12
