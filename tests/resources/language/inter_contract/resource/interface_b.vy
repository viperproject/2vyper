#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

from . import interface_a2
import tests.resources.language.inter_contract.resource.interface_a1 as Coin

#@ interface

#@ resource: b()

#@ ghost:
    #@ def a1() -> Coin: ...
    #@ def a2() -> interface_a2: ...

#@ invariant: sum(allocated[b]()) == 0
#@ invariant: sum(allocated[Coin.a[a1(self)]]()) == 0
#@ invariant: sum(allocated[interface_a2.a[a2(self)]]()) == 0

@public
def foo():
    raise "Not implemented"
