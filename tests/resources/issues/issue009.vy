#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ ensures: success() ==> result() == tuple(1, -1)
@private
def foo() -> (uint256, int128):
   return 1, -1

#@pure
@private
@constant
def pure_foo() -> (uint256, bool):
   return 42, False

#@ ensures: success() ==> result() == tuple(1, -1)
@public
def bar() -> (uint256, int128):
   return self.foo()

#@pure
@private
@constant
def pure_baz() -> (uint256, bool):
   u: uint256 = 1
   b: bool = True
   u, b = self.pure_foo()
   return u, b

#@ ensures: success() ==> result() == result(self.pure_foo())
#@ ensures: success() ==> result() == result(self.pure_baz())
@public
def baz() -> (uint256, bool):
   u: uint256 = 1
   b: bool = True
   u, b = self.pure_foo()
   return u, b
