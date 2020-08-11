#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def started() -> bool: ...
    #@ def owner() -> address: ...

# The owner stays the same
#@ invariant: owner(self) == old(owner(self))
# Once started, it stays started
#@ invariant: old(started(self)) ==> started(self)

# started flag is only modifiable by owner
#@ caller private: owner(self) == caller() ==> started(self)


#@ ensures: success() ==> result() == owner(self)
@public
@constant
def get_owner() -> address:
    raise "Not implemented"


#@ ensures: success() ==> result() == started(self)
@public
@constant
def is_started() -> bool:
    raise "Not implemented"


#@ ensures: msg.sender != owner(self) ==> revert()
#@ ensures: old(started(self)) ==> revert()
#@ ensures: success() ==> started(self)
@public
def start():
    raise "Not implemented"
