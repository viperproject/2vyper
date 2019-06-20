#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

mpp: map(int128, map(uint256, int128))
mp: map(address, int128)

fi: int128
ad: address


#@ ensures: self.fi == 0
#@ ensures: self.ad == ZERO_ADDRESS
#@ ensures: self.mp[self.ad] == 0
#@ ensures: self.mpp[10][10000] == 0
@public
def set():
    clear(self.fi)
    clear(self.ad)
    clear(self.mp[self.ad])
    clear(self.mpp[10][10000])


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.fi == 12
@public
def set2():
    self.fi = 12
    clear(self.fi)