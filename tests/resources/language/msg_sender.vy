#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

owner: address
b: bool


#@ invariant: self.owner == old(self.owner)
#@ always ensures: implies(msg.sender != self.owner, self.b == old(self.b))


@public
def __init__():
    self.owner = msg.sender


#@ ensures: implies(msg.sender != self.owner, self.b == old(self.b))
@public
def set_b(new_value: bool):
    assert msg.sender == self.owner
    self.b = new_value