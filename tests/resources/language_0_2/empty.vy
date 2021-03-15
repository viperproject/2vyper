# @version 0.2.x

#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: forall({i: uint256, j: uint256}, i < 2 and j < 5 ==> x[i][j] == 0)
@external
@view
def foo():
    x: uint256[2][5] = empty(uint256[2][5])


@external
@view
def bar(a: uint256,):
    x: uint256[2][5] = empty(uint256[2][5])