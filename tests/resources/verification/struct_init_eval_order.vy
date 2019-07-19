#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


struct Pair:
    first: int128
    second: int128
    

val: int128


@public
def set_and_ret(i: int128) -> int128:
    self.val = i
    return i
    

@public
def get_val() -> int128:
    return self.val
    

#@ ensures: implies(success(), self.val == 4)
@public
def f():
    p: Pair = Pair({second: self.set_and_ret(5), first: self.set_and_ret(4)})
