#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
def test():
    a: uint256 = bitwise_and(1, 2)
    b: uint256 = bitwise_or(a, a)
    c: uint256 = bitwise_xor(a, b)

    assert c >= 0, UNREACHABLE
