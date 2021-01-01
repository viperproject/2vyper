#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource

from . import interface

i: interface

#@ derived resource: token(f: uint256) -> interface.a[self.i]

#@ invariant: self.i == old(self.i)
#@ invariant: forall({a: address, v: uint256}, allocated[token(v)](a) == 0)

@public
def foo():
    pass