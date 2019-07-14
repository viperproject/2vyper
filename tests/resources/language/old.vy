#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

counter: int128

#@ invariant: self.counter <= old(self.counter)

#@ ensures: implies(success(), self.counter <= old(self.counter) - 2)
@public
def decr():
    self.counter -= 2
    send(ZERO_ADDRESS, as_wei_value(5, "wei"))