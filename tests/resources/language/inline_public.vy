#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

val: uint256
const_val: uint256
add: address


#:: Label(CC)
#@ invariant: self.const_val == old(self.const_val)


@public
def no_args_no_ret():
	pass


@public
def test1():
	self.no_args_no_ret()


#:: ExpectedOutput(invariant.violated:assertion.false, CC)
@public
def change_const_val():
	old_val: uint256 = 100
	self.const_val = 15


@public
def test2():
	old_val: uint256 = self.const_val
	self.change_const_val()
	self.const_val = old_val


@public
def args_no_ret(a: uint256):
	self.val = a


#@ ensures: self.val == 42
@public
def test3():
	self.args_no_ret(42)


@public
def no_args_ret() -> uint256:
	return 12


#@ ensures: self.val == 12
@public
def test4():
	self.val = self.no_args_ret()


@public
def args_ret(a: uint256) -> uint256:
	return a


#@ ensures: result() == a
@public
def test5(a: uint256) -> uint256:
	return a


@public
def inc(by: uint256):
	b: uint256 = by
	self.val += b


@public
def inc2(by: uint256):
	for i in range(2):
		self.inc(by)


#@ ensures: self.val == old(self.val) + 7 * by
@public
def test6(by: uint256):
	self.inc(by)
	self.inc(by)
	self.inc(by)
	self.inc(by)
	self.inc(by)
	self.inc2(by)


@public
def set_add():
    self.add = msg.sender


#@ ensures: result() == True
@public
def test7() -> bool:
    self.set_add()
    a: address = self.add
    self.set_add()
    return a == self.add