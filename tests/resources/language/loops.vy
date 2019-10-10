#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

CONST: constant(int128) = 12

#@ ensures: implies(success(), result() == 5)
@public
def simple_loop() -> int128:
	res: int128 = 0
	for i in range(5):
		res = res + 1
	return res

#@ ensures: implies(success(), result() == 50 * 49 / 2)
@public
def sum_of_numbers() -> int128:
	res: int128 = 0
	for i in range(0, 0 + 50):
		res += i
	return res

#@ ensures: implies(success(), result() == 50 * at + 50 * 49 / 2)
@public
def sum_of_numbers_starting(at: int128) -> int128:
	res: int128 = 0
	for i in range(at, at + 50):
		res += i
	return res

#@ ensures: implies(success(), result() == 10)
@public
def pairs() -> int128:
	res: int128 = 0
	for i in range(10):
		for j in range(10):
			if i == j:
				res += 1
	return res

#@ ensures: implies(success(), result() == (start < 20))
@public
def loop_with_break(start: int128) -> bool:
	assert start >= 0
	res: bool = False
	for i in range(start, start + 20):
		if i == 2 * start:
			res = True
			break
		res = False
	return res

#@ ensures: implies(success(), result() == (4 if start % 2 == 0 else 5))
@public
def loop_with_continue(start: int128) -> int128:
	res: int128 = 0
	for i in range(start, start + 9):
		if i % 2 == 0:
			continue
		else:
			res += 1
	return res

#@ ensures: implies(success(), res == 12)
@public
def for_in_loop(array: int128[12]) -> int128:
	res: int128 = 0
	for i in array:
		res += 1
	return res

@public
def for_in_loop_element():
	array: int128[12] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
	idx: int128 = 0
	for i in array:
		idx += 1
		assert i == idx, UNREACHABLE

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() == 5)
@public
def nested_loop_fail() -> int128:
	res: int128 = 0
	for i in range(5):
		if i == 2:
			break
		if i == 5:
			continue
		for j in range(2):
			res = res + j
	else:
		res = 5
	return res
