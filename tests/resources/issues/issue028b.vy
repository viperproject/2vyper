#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import issue028a

#@ config: trust_casts

a: issue028a

#@ invariant: self.a == old(self.a)


@public
def __init__(a_address: address):
    assert a_address != self and a_address != ZERO_ADDRESS
    self.a = issue028a(a_address)
    assert self.a == a_address
    assert self.a != self and self.a != ZERO_ADDRESS


#@ ensures: success() ==> getval(self.a, self.a) == 0
@public
def test():
    self.a.foo()
