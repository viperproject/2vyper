#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import mana_continuous_sale_interface

#@ interface

#@ ghost:
    #@ def owner() -> address: ...

#@ caller private: conditional(owner(self) == caller(), owner(self))


#@ ensures: success() ==> result() == owner(self)
@public
@constant
def get_owner() -> address:
    raise "Not implemented"


#@ ensures: msg.sender != old(owner(self)) ==> revert()
#@ ensures: success() ==> owner(self) == newOwner
@public
def transferOwnership(newOwner: address):
    raise "Not implemented"