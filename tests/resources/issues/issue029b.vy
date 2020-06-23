#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

val: int128

#:: ExpectedOutput(invariant.not.wellformed:reflexivity.violated)
#@ invariant: old(self.val) == 0

@public
def test():
    # self.val == 0
    self.val += 1
    # self.val == 1
    # Therefore, self.val == 1 and old(self.val) == 0 is part of the relation.
    # But, self.val == 1 and old(self.val) == 1 is not part of the relation.
    # -> This invariant is not reflexive.
