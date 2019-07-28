#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


large: uint256
small: uint256


#@ invariant: self.large >= self.small
#@ invariant: self.large >= old(self.large)
#@ invariant: self.small <= old(self.small)


@public
def __init__(initial_val: uint256):
    self.large = initial_val
    self.small = initial_val


@public
def increment():
    self.large += 1


@public
def decrement():
    self.small -= 1


#@ ensures: implies(success(), implies(issued(self.large) > i, self.large > 2 * i))
@public
def foo(i: uint256):
    self.large += i


#@ ensures: implies(i < old(self.small), success(if_not=sender_failed))
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(i < issued(self.small), success(if_not=sender_failed))
@public
def bar(i: uint256):
    self.small -= i