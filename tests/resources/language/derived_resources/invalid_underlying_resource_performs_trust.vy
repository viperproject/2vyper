#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

from . import interface

i: interface

#@ derived resource: token() -> interface.r[self.i]

#@ invariant: forall({a: address}, allocated[token](a) == 0)

#:: ExpectedOutput(carbon)(derived.resource.invariant.failed:underlying.address.trust)
@public
def foo():
    #:: ExpectedOutput(derived.resource.invariant.failed:underlying.address.trust)
    self.i.trust()