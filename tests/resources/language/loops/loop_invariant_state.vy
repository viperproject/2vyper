#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

t: int128[23875682375]

@public
def foo(a: int128):
    for i in self.t:
        #@ invariant: self.t == old(self.t)
        #@ invariant: loop_array(i)[loop_iteration(i)] == self.t[loop_iteration(i)]
        pass
