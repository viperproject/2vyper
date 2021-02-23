# @version 0.2.8

#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

list: int128[2]


#@ ensures: success() ==> result()
#@ ensures: success() ==> 0 not in self.list
@external
def foo() -> bool:
    self.list = [1, 2]
    return 0 not in self.list


#@ ensures: success() ==> result()
@external
def bar() -> bool:
    return 0 not in [1, 2]


#@ ensures: success() ==> not result()
@external
def baz() -> bool:
    return 0 not in [0, 1, 2]
