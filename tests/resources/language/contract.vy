#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract List:
    def at(index: uint256) -> int128: constant
    def update(index: uint256, value: int128): modifying
    def append(value: int128): modifying
    def extend(values: int128[2]): modifying


ll: List
cval: int128
val: int128
ended: bool


#@ invariant: self.ll == old(self.ll)
#:: Label(CONST)
#@ invariant: self.cval == old(self.cval)
#@ invariant: implies(old(self.ended), self.ended)
#@ invariant: implies(self.ended, forall({a: address}, {sent(a)}, old(sent(a) == sent(a))))


@public
def __init__(l: address):
    self.ll = List(l)


@public
def set_val(i: int128):
    self.val = i


@public
def test_list():
    self.ll.append(1)
    self.ll.extend([1, 2])
    self.ll.update(0, 4)
    assert self.ll.at(0) == 4


#@ ensures: self.cval == old(self.cval)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.val == old(self.val)
@public
def list_reentrance():
    self.ll.append(0)


#@ ensures: sent(self.ll) >= old(sent(self.ll))
#@ ensures: implies(success(), sent(self.ll) - old(sent(self.ll)) >= msg.value)
@public
@payable
def send_call():
    assert not self.ended
    self.ll.update(0, 1, value=msg.value)


@public
def update_list(i: uint256, v: int128):
    self.cval = -1
    #:: ExpectedOutput(call.invariant:assertion.false, CONST)
    self.ll.update(i, v)


@public
def use_ret(i: uint256) -> int128:
    self.ll.update(i, 5)
    return self.ll.at(i)
