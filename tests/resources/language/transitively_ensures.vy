#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract Owner:
    def tell(): modifying


lock: bool
val: int128
owner: Owner


#@ preserves:
    #:: Label(LOCK)
    #@ always ensures: implies(old(self.lock), self.lock and self.val == old(self.val))


@public
def __init__():
    self.owner = Owner(msg.sender)


@public
def set_val(new_val: int128):
    assert not self.lock
    self.val = new_val


#@ ensures: self.val == old(self.val)
@public
def tell_owner():
    assert not self.lock
    self.lock = True
    self.owner.tell()
    self.lock = False


#:: ExpectedOutput(postcondition.violated:assertion.false, LOCK)
@public
def set_val_fail(new_val: int128):
    self.val = new_val
