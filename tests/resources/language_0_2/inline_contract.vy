# @version 0.2.x

#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

interface FooBar:
    def test1() -> uint256: pure
    def test2() -> uint256: view
    def test3() -> uint256: nonpayable
    def test4() -> uint256: payable

@external
def normal(a: address) -> int128:
    FooBar(a).test1()
    FooBar(a).test2()
    FooBar(a).test3()
    FooBar(a).test4(value=4)
    return 5
