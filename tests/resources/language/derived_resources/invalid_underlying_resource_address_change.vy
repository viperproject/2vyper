#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

from . import interface

i: interface
a: interface

m: map(address, uint256)

#@ preserves:
    #@ always ensures: trust_no_one(self, self.a)
    #@ always ensures: no_offers[interface.r[self.a]](self)

#@ derived resource: token() -> interface.r[self.i]

#@ inter contract invariant: trust_no_one(self, self.a)
#@ inter contract invariant: no_offers[interface.r[self.a]](self)

#@ invariant: self != self.a
#@ invariant: allocated[token]() == self.m

#:: ExpectedOutput(derived.resource.invariant.failed:underlying.address.constant)
@public
def foo():
    self.i = self.a