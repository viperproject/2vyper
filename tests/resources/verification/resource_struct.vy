#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


struct R:
    i: int128
    j: int128


#@ resource: R(i: int128, b: bool)

#@ invariant: forall({a: address}, {allocated[wei](a)}, allocated[wei](a) == 0)
#@ invariant: forall({a: address, i: int128, b: bool}, {allocated[R(i, b)](a)}, allocated[R(i, b)](a) == 0)


#@ ensures: R({i: 1, j: 1}) == R({i: 1, j: 1})
@public
def check():
    pass
