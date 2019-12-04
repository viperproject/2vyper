#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract C:
    def f(): modifying


val: int128


#@ preserves:
    #@ always ensures: issued(self.val == 12) ==> self.val >= old(self.val)


@public
@payable
def increment_val():
    self.val += 1


@public
def pay():
    C(msg.sender).f(value=self.balance)
