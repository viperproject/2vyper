#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ ensures: len(b) >= 37 ==> success(if_not=out_of_gas)
@public
@constant
def extract_bytes32_default(b: bytes[40]) -> bytes32:
    return extract32(b, 5)


#@ ensures: len(b) < 32 ==> revert()
@public
@constant
def extract_bytes32(b: bytes[32]) -> bytes32:
    return extract32(b, 0, type=bytes32)

@public
@constant
def extract_int128(b: bytes[32]) -> int128:
    return extract32(b, 0, type=int128)

@public
@constant
def extract_address(b: bytes[32]) -> address:
    return extract32(b, 0, type=address)
