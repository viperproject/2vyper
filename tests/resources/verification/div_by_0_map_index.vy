#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

mp: map(int128, uint256)
mpp: map(int128, map(int128, uint256))

#@ ensures: implies(a == 0, not success())
@public
def div(a: int128):
    self.mp[100 / a] = 12


#@ ensures: implies(a == 0, not success())
@public
def div2(a: int128):
    self.mpp[1 / a][100] = 12


#@ ensures: implies(a == 0, not success())
@public
def div3(a: int128):
    self.mp[1 / a] += 12