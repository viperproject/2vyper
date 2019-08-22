#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

counter: int128
nt_counter: int128


#@ transitive:
    #@ always ensures: self.counter <= old(self.counter)
    #:: ExpectedOutput(postcondition.not.wellformed:transitivity.violated)
    #@ always ensures: self.nt_counter == old(self.nt_counter) or self.nt_counter == old(self.nt_counter) + 1


@public
def dec():
    old_counter: int128 = self.counter
    send(ZERO_ADDRESS, as_wei_value(1, "wei"))
    self.counter = old_counter - 1
