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

#@ invariant: sum(allocated[b]()) == 0
#@ invariant: sum(allocated[interface_a2.a]()) == 0
#@ invariant: sum(allocated[Coin.a]()) == 0

@public
def foo():
    raise "Not implemented"