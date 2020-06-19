#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import issue030a

#@ config: trust_casts

a: issue030a

#@ preserves:
    #@ always ensures: _val(self.a) == 0
    #@ always ensures: old(_val(self.a)) == 0

#@ invariant: self.a == old(self.a)

@public
def __init__(a_address: address):
    self.a = issue030a(a_address)
    self.a.set_0()
