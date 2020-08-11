#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def token_owner() -> address: ...

#@ ensures: success() ==> result() == token_owner(self)
@public
@constant
def get_owner() -> address:
    raise "Not implemented"


# caller private: conditional(owner(self) == caller(), owner(self))


#@ ensures: msg.sender != old(token_owner(self)) ==> revert()
#@ ensures: success() ==> token_owner(self) == newOwner
@public
def transferOwnership(newOwner: address):
    raise "Not implemented"