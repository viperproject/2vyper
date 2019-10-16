#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas, no_overflows


val: int128

@public
def __init__(a: int128, b: int128):
    self.val = a ** b


#@ ensures: result() >= 1
@public
def pow(a: uint256, b: uint256) -> uint256:
    return a ** b + 1