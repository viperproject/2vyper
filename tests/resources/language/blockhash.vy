#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: block.number > 5 + 256 ==> not success()
@public
def get_blockhash_5() -> bytes32:
    return blockhash(5)


#@ ensures: block.number - 256 <= u and u < block.number ==> success(if_not=out_of_gas)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: u == block.number ==> success(if_not=out_of_gas)
@public
def get_blockhash(u: uint256) -> bytes32:
    return blockhash(u)
