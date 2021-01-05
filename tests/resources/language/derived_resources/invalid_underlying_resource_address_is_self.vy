#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

from . import interface
implements: interface

i: interface

#:: ExpectedOutput(derived.resource.invariant.failed:underlying.address.self)
#@ derived resource: token() -> r[self]

#@ invariant: forall({a: address}, allocated[token](a) == 0)
#@ invariant: forall({a: address}, allocated[r](a) == 0)
#@ invariant: forall({a: address, v: uint256}, allocated[interface.a(v)](a) == 0)

@public
def foo():
    pass

@public
def offer_r():
    pass

@public
def trust():
    pass

@public
def create_r():
    pass

@public
def reallocate_r():
    pass