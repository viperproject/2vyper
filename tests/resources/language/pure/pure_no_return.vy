#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@pure
@constant
@private
def check_arg(i: int128):
    assert i > 0


#@ ensures: success() ==> i > 0 and j < 0
@public
def foo(i: int128, j: int128):
    self.check_arg(i)
    self.check_arg(-j)

#@ ensures: success(self.check_arg(i)) ==> i > 0
#@ ensures: success(self.check_arg(-i + 1)) ==> i <= 0
@public
def bar(i: int128):
    pass