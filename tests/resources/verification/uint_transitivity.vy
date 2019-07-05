#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


i: uint256
arr: int128[5]


#@ invariant: self.arr[4] == 0
#@ invariant: self.arr[4] == old(self.arr[4])
#@ invariant: self.i < 1
#@ invariant: self.i == old(self.i) or self.i == old(self.i - 1)


@public
def f():
    self.i = 0
