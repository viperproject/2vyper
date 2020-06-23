#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

a: int128
b: int128

#:: Label(POST)
#@ always ensures: result(self.get_a()) >= old(result(self.get_a()))

#@ pure
@private
@constant
def get_a() -> int128:
    return self.a

#@ ensures: success() ==> (pre == post)
@public
def foo(cond: bool):
    pre_a: int128 = self.a
    pre: int128 = 0
    post: int128 = 0
    if cond:
        self.a = 1
        self.b = 2
        pre = self.get_a()
    else:
        self.a = 3
        self.b = 4
        post = self.get_a()

    if cond:
        self.a = 1
        self.b = 4
        post = self.get_a()
    else:
        self.a = 3
        self.b = 2
        pre = self.get_a()

    self.a = pre_a

#@ ensures: success() ==> (pre == post)
@public
def bar(cond: bool):
    pre: int128 = self.get_a()
    self.b = 42
    post: int128 = self.get_a()

@public
def compliant():
    self.a += 1

#:: ExpectedOutput(postcondition.violated:assertion.false, POST)
@public
def not_compliant():
    self.a = 1