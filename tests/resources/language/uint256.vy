#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas, no_overflows


ui: uint256
mp: map(int128, uint256)
array: uint256[10]
mp_arr: map(int128, uint256[2])

#@ ensures: self.ui >= 0
@public
def simple():
    pass

#@ ensures: result() >= 0
@public
def calc() -> uint256:
    return self.mp[100]

#@ ensures: result() >= 0
@public
def args(arg: uint256) -> uint256:
    return arg

#@ ensures: result() >= 0
@public
def _add(a: uint256, b: uint256) -> uint256:
    return a + b * a + a * b

#@ ensures: success()
@public
def _div(a: uint256, b: uint256) -> uint256:
    return a / (b + 1)

#@ ensures: not success()
@public
def fail(a: uint256, b: uint256) -> uint256:
    assert a > b
    self.ui = b - a
    return self.ui

#@ ensures: success()
@public
def access_arr_map():
    assert self.ui >= 0
    assert self.mp[2] >= 0
    assert self.array[2] >= 0
    assert self.mp_arr[2][1] >= 0

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success()
@public
def access_arr_map_fail():
    assert self.ui >= 0
    assert self.mp[2] >= 0
    assert self.array[2] >= 0
    assert self.mp_arr[2][1] >= 0
    assert self.mp_arr[2][1] >= 1


#@ ensures: result() >= 0
#@ ensures: result() == a[2]
@public
def pass_array(a: uint256[5]) -> uint256:
    assert a[0] >= 0
    assert a[1] >= 0
    assert a[4] >= 0
    return a[2]
