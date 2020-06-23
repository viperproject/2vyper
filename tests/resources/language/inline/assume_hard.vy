#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Verification took   4.33 seconds. [benchmark=10] (With assume_private_function)
# Verification took   4.17 seconds. [benchmark=10] (With inline)

contract C:
    def f(): modifying

lock: bool
val: int128

#@ invariant: self.val >= old(self.val)

#@ preserves:
    #@ always ensures: old(self.lock) ==> (self.lock and self.val == old(self.val))

#@ requires: self.lock == False
#@ requires: self.val >= public_old(self.val)
#@ ensures: addr == msg.sender ==> success(if_not=sender_failed)
#@ ensures: self.val >= public_old(self.val)
@private
def call_Cf_modifying(addr: address):
    C(addr).f()

#@ requires: addr == msg.sender
#@ requires: self.val >= public_old(self.val)
#@ ensures: self.val == old(self.val)
#@ ensures: success() ==> result() == public_old(self.val)
#@ ensures: success(if_not=sender_failed)
@private
def call_Cf_non_modifying(addr: address) -> int128:
    temp_val: int128 = self.val
    temp_lock: bool = self.lock
    self.lock = False
    C(addr).f()
    ret_val: int128 = self.val
    self.val = temp_val
    self.lock = temp_lock
    return ret_val


@public
def set_val(a: int128):
    assert not self.lock
    if a > self.val:
        self.val = a

#@ ensures: not self.lock ==> success(if_not=sender_failed)
@public
def foo():
    assert not self.lock
    self.lock = True
    old_val: int128 = self.val
    new_val: int128 = self.call_Cf_non_modifying(msg.sender)
    if new_val > old_val:
        self.val = new_val
    self.lock = False

#@ ensures: not self.lock ==> success(if_not=sender_failed)
@public
def bar():
    assert not self.lock
    self.call_Cf_modifying(msg.sender)

@public
def baz():
    assert not self.lock
    self.lock = True
    C(msg.sender).f()
    self.lock = False
