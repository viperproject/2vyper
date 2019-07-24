#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


val: uint256
const_val: uint256


#@ invariant: self.const_val == old(self.const_val)


@private
def no_args_no_ret():
	pass


@public
def test1():
	self.no_args_no_ret()


@private
def change_const_val():
	old_val: uint256 = 100
	self.const_val = 15


@public
def test2():
	old_val: uint256 = self.const_val
	self.change_const_val()
	self.const_val = old_val


@private
def args_no_ret(a: uint256):
	self.val = a


#@ ensures: self.val == 42
@public
def test3():
	self.args_no_ret(42)


@private
def no_args_ret() -> uint256:
	return 12


#@ ensures: self.val == 12
@public
def test4():
	self.val = self.no_args_ret()


@private
def args_ret(a: uint256) -> uint256:
	return a


#@ ensures: result() == a
@public
def test5(a: uint256) -> uint256:
	return a


@private
def inc(by: uint256):
	b: uint256 = by
	self.val += b


@private
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
