#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

import tests.resources.allocation.ico.gvtoken_interface_alloc as GVT

#@ interface

#@ ghost:
    #@ def new_token() -> GVT: ...

#@ performs: reallocate[GVT.token[new_token(self)]](_value, to=_from, actor=self)
#@ ensures: success() ==> storage(_from) == old(storage(_from))
#@ ensures: msg.sender == old(new_token(self)) ==> revert()
#@ ensures: _from == old(new_token(self)) ==> revert()
@public
def migrateFrom(_from: address, _value: uint256):
    raise "Not implemented"