#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


mp: map(int128, int128)

#:: Label(SUM_CONST)
#@ invariant: old(sum(self.mp)) == sum(self.mp)

#@ ensures: sum(self.mp) == 0
@public
def __init__():
    pass

@public
def change_mp():
    self.mp[12] += 10
    self.mp[13] -= 10

#:: ExpectedOutput(invariant.violated:assertion.false, SUM_CONST)
@public
def change_mp_wrong():
    self.mp[42] = 0