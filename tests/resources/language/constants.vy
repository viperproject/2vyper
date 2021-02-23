#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

c1: constant(int128) = 12
c2: constant(int128) = 12 + 12 * 2 * 4 - 3
c3: constant(int128) = 12 / 5
c4: constant(bool) = True and False and not True
c5: constant(bool) = not True or False or True
c6: constant(bool) = True and False
c7: constant(int128) = min(c1, c2)
c8: constant(int128) = max(c7, 1 + 3)
c9: constant(int128) = 12 / -5
c10: constant(uint256[3]) = [convert(1, uint256), convert(2, uint256), convert(3, uint256)]


@public
def sum_c1_c2() -> int128:
    return c1 + c2

#@ ensures: success() ==> result() == 12 / 5
@public
def get_c3() -> int128:
    return c3

#@ ensures: success() ==> result() == 12 / -5
@public
def get_c9() -> int128:
    return c9

@public
def bool_ops() -> bool:
    b: bool = c6
    b = c5
    b = c4
    return b

#@ ensures: success() ==> result()[0] == 1
#@ ensures: success() ==> result()[1] == 2
#@ ensures: success() ==> result()[2] == 3
@public
def get_c10() -> uint256[3]:
    return c10

#@ ensures: success() ==> result() == 0x0000000000000000000000000000000000000000
@public
def _zero_address() -> address:
    return ZERO_ADDRESS

#@ ensures: success() ==> len(result()) == 32
@public
def _empty_bytes32() -> bytes32:
    return EMPTY_BYTES32

#@ ensures: success() ==> result() == 0
@public
def _zero_wei() -> wei_value:
    return ZERO_WEI

#@ ensures: success() ==> result() == 170141183460469231731687303715884105727
@public
def _max_int128() -> int128:
    return MAX_INT128
