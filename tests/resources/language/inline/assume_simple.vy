#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Verification took   3.35 seconds. [benchmark=10] (With assume_private_function)
# Verification took   2.99 seconds. [benchmark=10] (With inline)

a: int128
b: int128

#@ invariant: self.a <= self.b
#@ invariant: self.a >= 0 and self.b >= 0

#@ ensures: success() ==> (result() >= 0 and (result() + 1) == (block.number / (2 ** 129)))
@private
@constant
def get_block_num_in_int128() -> int128:
    local: uint256 = block.number / (2 ** 129) - 1
    return convert(local, int128)

#@ ensures: success() ==> self.b == val
#@ ensures: forall({a: address}, a != self ==> storage(a) == old(storage(a))) and self.a == old(self.a)
@private
def set_b(val: int128):
    self.b = val

#@ ensures: success() ==> (self.a > self.b and self.a == old(self.a))
#@ ensures: (success() ==> result() == local2 + a) and (local2 == 42)
@private
def foo(a: int128) -> int128:
    local1: int128 = -1
    local2: int128 = 42
    self.set_b(self.a + local1)
    return local2 + a


#@ ensures: success() ==> (self.a == 3598 and self.b == 45918 and local1 == 23432)
@public
def call1():
    local1: int128 = 23432
    self.a = 3598
    local2: int128 = self.foo(45876)
    self.set_b(local2)

#@ ensures: success() ==> (self.a == self.b)
@public
def set_a_and_b_to_block_num():
    self.a = self.get_block_num_in_int128()
    self.b = self.get_block_num_in_int128()
