#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

val1: int128
val2: int128

#@ ensures: success() ==> independent(result(), self.val2)
# ensures: success() ==> result() == self.val1
@constant
@private
def get_val1() -> int128:
    return self.val1

#@ ensures: self.val2 == old(self.val2)
#@ ensures: success() ==> self.val1 == val
@private
def set_val1(val: int128):
    self.val1 = val

#@ ensures: success() ==> independent(result(), self.val1)
# ensures: success() ==> result() == self.val2
@constant
@private
def get_val2() -> int128:
    return self.val2

#@ ensures: self.val1 == old(self.val1)
#@ ensures: success() ==> self.val2 == val
@private
def set_val2(val: int128):
    self.val2 = val

#@ ensures: success() ==> independent(before, self.val2) and independent(after, self.val2)
# ensures: success() ==> before == after
@public
def foo():
    before: int128 = self.get_val1()
    self.val2 = 42
    after: int128 = self.get_val1()

# ensures: success() ==> before == after
@public
def bar():
    before: int128 = self.get_val1()
    self.set_val2(42)
    after: int128 = self.get_val1()
