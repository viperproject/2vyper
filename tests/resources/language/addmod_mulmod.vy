#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


#@ ensures: a == 15 and b == 6 and m == 2 ==> result() == 1
#@ ensures: a == 19 and b == 1 and m == 5 ==> result() == 0
#@ ensures: m == 0 ==> revert()
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: a == 12 and b == 2 and m == 2 ==> result() == 1
@public
def _addmod(a: uint256, b: uint256, m: uint256) -> uint256:
    return uint256_addmod(a, b, m)


#@ ensures: a == 15 and b == 6 and m == 2 ==> result() == 0
#@ ensures: a == 19 and b == 1 and m == 5 ==> result() == 4
#@ ensures: m == 0 ==> revert()
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: a == 12 and b == 2 and m == 2 ==> result() == 1
@public
def _mulmod(a: uint256, b: uint256, m: uint256) -> uint256:
    return uint256_mulmod(a, b, m)