#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


array: int128[12]
matrix: int128[12][12]
tensor: int128[2][2][2]

zeros: int128[1000]

mp: map(int128, int128[10])

#:: Label(CONST_ZEROS)
#@ invariant: self.zeros == old(self.zeros)


@public
def array_read() -> int128:
    a: int128 = self.array[5]
    return a + self.matrix[4][7] + self.tensor[0][1][0]


#@ ensures: result() == 10
@public
def array_write() -> int128:
    self.array[0] = 10
    return self.array[0]


#@ ensures: forall({i: int128}, {self.array[i]}, implies(0 <= i and i < 12, self.array[i] == 42))
@public
def array_write_all():
    for i in range(12):
        self.array[i] = 42


#@ ensures: result() == 100
@public
def matrix_write() -> int128:
    a: int128[12] = self.array
    a[11] = 10
    i: int128 = a[11]
    self.matrix[1][2] = i
    self.matrix[1][2] = 100
    return self.matrix[1][2]


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() == 101
@public
def matrix_write_fail() -> int128:
    a: int128[12] = self.array
    a[11] = 10
    i: int128 = a[11]
    self.matrix[1][2] = i
    self.matrix[1][2] = 100
    return self.matrix[1][2]


#@ ensures: revert()
@public
def out_of_bounds_read():
    i: int128 = 42
    a: int128 = self.array[i]


#@ ensures: revert()
@public
def out_of_bounds_write():
    i: int128 = 42
    self.array[i] = 12


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() == 0
@public
def get_zeros_fail() -> int128:
    i: int128 = 1000
    return self.zeros[i]


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() == 0
@public
def get_zeros_at_fail(i: int128) -> int128:
    return self.zeros[i]


#:: ExpectedOutput(invariant.violated:assertion.false, CONST_ZEROS)
@public
def set_zeros_fail():
    self.zeros[12] = 100


@public
def acc_map():
    self.mp[1][2] = 5


#@ ensures: revert()
@public
def acc_bounds() -> int128:
    i: int128 = 1000
    return self.mp[2][i]


#:: ExpectedOutput(not.wellformed:seq.index.negative) | ExpectedOutput(carbon)(postcondition.violated:assertion.false)
#@ ensures: implies(n < 5, a[n] == 0)
@public
def index_negative_fail(a: int128[5], n: int128):
    pass


#:: ExpectedOutput(not.wellformed:seq.index.length) | ExpectedOutput(carbon)(postcondition.violated:assertion.false)
#@ ensures: implies(n >= 0, a[n] == 0)
@public
def index_size_fail(a: int128[5], n: int128):
    pass