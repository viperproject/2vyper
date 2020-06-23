#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


contract C:
    def f() -> bool: modifying


c: C
f1: int128
f2: int128


#@ invariant: self.f1 > self.f2


@public
def __init__():
    self.c = C(msg.sender)
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
def times_assert_unreachable_fail(val: int128) -> int128:
    res: int128 = 2 * val
    #:: ExpectedOutput(assert.failed:assertion.false)
    assert res > val, UNREACHABLE
    return res


@public
def assert_property():
    assert -1 + 1 == 0, UNREACHABLE


@public
@payable
def assert_ghost_property():
    #@ assert old(sum(sent()) == 0) ==> sum(sent()) == 0, UNREACHABLE

    #@ if old(received(msg.sender)) == 0 and received(msg.sender) > 12:
        #@ assert msg.value > 4, UNREACHABLE
    #@ elif old(received(msg.sender)) == 0:
        #@ assert msg.value < 16, UNREACHABLE
    #@ else:
        #@ assert msg.value >= 0, UNREACHABLE

    #:: ExpectedOutput(assert.failed:assertion.false)
    #@ raise UNREACHABLE

    pass

#@ ensures: success()
@public
def assert_modifiable_const(val: uint256):
    assert_modifiable(val >= 0)


@public
def assert_modifiable_mut(val: uint256):
    assert_modifiable(self.c.f())


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success()
@public
def assert_modifiable_fail(val: uint256):
    assert_modifiable(self.c.f())
