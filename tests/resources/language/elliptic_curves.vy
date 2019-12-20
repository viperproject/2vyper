#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
def get_ecrecover(h: bytes32, v: uint256, r: uint256, s: uint256) -> address:
    return ecrecover(h, v, r, s)

@public
def get_ecadd(a: uint256[2], b: uint256[2]) -> uint256[2]:
    return ecadd(a, b)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success(if_not=out_of_gas or overflow)
@public
def get_ecmul(v: uint256[2], s: uint256) -> uint256[2]:
    return ecmul(v, s)
