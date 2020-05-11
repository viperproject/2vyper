#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract C:
    def f(): modifying


c: C
val: int128


@public
def __init__():
    self.c = C(msg.sender)


#:: Label(INV)
#@ invariant: self.val == 0


@private
def use_assert_unreachable(a: int128):
    #:: ExpectedOutput(assert.failed:assertion.false) | ExpectedOutput(assert.failed:assertion.false, UAC)
    assert a == 0, UNREACHABLE


@public
def call_use_assert_unreachable_fail():
    #:: Label(UAC)
    self.use_assert_unreachable(42)


@private
def inner(a: int128):
    #:: ExpectedOutput(assert.failed:assertion.false) | ExpectedOutput(assert.failed:assertion.false, IC) | ExpectedOutput(assert.failed:assertion.false, IC, OC)
    assert a == 0, UNREACHABLE


@private
def outer(a: int128):
    #:: Label(IC)
    self.inner(a)


@public
def call_outer_fail():
    #:: Label(OC)
    self.outer(42)


@private
def call_ext():
    self.val = 1
    #:: ExpectedOutput(call.invariant:assertion.false, INV) | ExpectedOutput(call.invariant:assertion.false, CEC, INV)
    self.c.f()
    self.val = 0


@public
def call_ext_fail():
    #:: Label(CEC)
    self.call_ext()
