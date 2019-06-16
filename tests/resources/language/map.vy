#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

mp: map(int128, int128)
i: int128

#@ invariant: self.i == 0
#:: Label(MP)
#@ invariant: self.mp[self.i] == 0

@public
def __init__():
    self.i = 20
    self.i = self.mp[self.i]


#@ ensures: self.mp[100] == 8
@public
def write_map():
    self.mp[100] = 8


@public
def write_mult():
    self.mp[self.i] = 10
    self.mp[self.i] = 0


# Should fail
#:: ExpectedOutput(invariant.violated:assertion.false, MP)
@public
def write_wrong():
    self.mp[self.i] = 42
