#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@pure
@constant
@private
def private_add_numbers(i: int128, j: int128 = 1) -> int128:
    return i + j

#@pure
@constant
@private
def private_plus_one(i: int128 = 0) -> int128:
    return self.private_add_numbers(i)


#@ ensures: success() ==> result() == i + j + 1
#@ ensures: result(self.private_plus_one()) == 1
#@ ensures: result(self.private_plus_one(1)) == 2
#@ ensures: result(self.private_add_numbers(2)) == 3
#@ ensures: result(self.private_add_numbers(40, 2)) == 42
@public
def add_many_numbers(i: int128, j: int128) -> int128:
    first: int128 = self.private_add_numbers(i, j)
    second: int128 = self.private_add_numbers(first)
    return second


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result(self.private_add_numbers(1)) == 1
@public
def foo_fail():
    pass