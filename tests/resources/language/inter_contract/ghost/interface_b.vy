#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import interface_a2
import tests.resources.language.inter_contract.ghost.interface_a1 as Coin

#@ interface

#@ ghost:
    #@ def b() -> int128: ...
    #@ def owner() -> address: ...


#@ inter contract invariant: interface_a2.a(owner(self)) == 42
#@ inter contract invariant: Coin.a(owner(self)) == 42

@public
def foo():
    raise "Not implemented"
