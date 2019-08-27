#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

val: int128


#@ ensures: implies(success(), reorder_independent(self.val))
@public
def set_val(new_val: int128):
    self.val = new_val


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: reorder_independent(self.val)
@public
def inc_val():
    self.val += 1
