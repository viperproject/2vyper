#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

mp: map(int128, int128)
mpp: map(int128, map(int128, int128))

i: int128

#@ ensures: self.i == self.mp[12] + 4
@public
def set_i():
    self.i = self.mp[12] + 4

@public
def get_12_13() -> int128:
    return self.mpp[12][13]