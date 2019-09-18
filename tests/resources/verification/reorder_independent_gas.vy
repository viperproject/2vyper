#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


val: int128
work: public(int128)


# Not reorder independent because of different uses of gas in the different branches
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: reorder_independent(self.val)
@public
def set_val(new_val: int128):
    if self.work == 0:
        self.work = new_val ** 2
        self.val = new_val
    else:
        self.val = new_val
