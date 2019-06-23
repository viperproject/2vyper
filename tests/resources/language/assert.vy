#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

f1: int128
f2: int128


#@ invariant: self.f1 > self.f2


@public
def __init__():
    self.f1 = 12
    self.f2 = 11


#@ ensures: result() == 5
@public
def assert_true() -> int128:
    assert True
    return 5


@public
def set(val: int128):
    assert val > self.f2
    self.f1 = val


@public
def assert_label(val: int128):
    assert val > self.f2, "Error"


@public
def assert_unreachable(val: uint256):
    assert val >= 0, UNREACHABLE


@public
def assert_unreachable_fail(val: int128):
    #:: ExpectedOutput(assert.failed:assertion.false)
    assert False, UNREACHABLE


@public
def assert_property():
    assert -1 + 1 == 0, UNREACHABLE
