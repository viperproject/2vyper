#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

val: int128

#:: ExpectedOutput(invariant.not.wellformed:reflexivity.violated)
#@ invariant: old(self.val) != 0 ==> self.val == old(self.val) + 1

#@ ensures: success() ==> self.val != old(self.val) + 1
@public
def set_val(new_val: int128):
    assert new_val != self.val + 1
    self.val = new_val