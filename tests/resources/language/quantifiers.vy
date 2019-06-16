#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

mp: map(int128, int128)

#:: Label(QT)
#@ invariant: forall({i: int128}, {self.mp[i]}, self.mp[i] == 0)


@public
def no_change():
    pass


@public
def no_change2():
    self.mp[4] = 1
    self.mp[4] = 0


#:: ExpectedOutput(invariant.violated:assertion.false, QT)
@public
def change():
    self.mp[0] = 42

