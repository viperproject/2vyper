#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
def times(a: decimal, b: decimal) -> decimal:
    return a * b


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success() ==> a > 0.0 and a <= 1.0 ==> a == 1.0
@public
def gaps_fail(a: decimal) -> decimal:
    return a


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success() and a > 0.0, result() <= a)
@public
def invert_fail(a: decimal) -> decimal:
    return 1.0 / a


#@ ensures: 2.0 / 2.0 == 1.0
#@ ensures: 0.0 < 1.0 / 2.0 and 1.0 / 2.0 < 1.0
#@ ensures: 2.0 + 1.0 / 2.0 - 3.0 / 2.0 == 1.0
#@ ensures: 2.1 + 0.9 == 3.0
#@ ensures: convert(2.0, int128) == 2
#@ ensures: convert(3.1, int128) == 3
#@ ensures: 2.123456789 + 3.987654321 < 7.0
#@ ensures: convert(2.1234 * 10000.0, uint256) == 21234
@public
def check():
    pass


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: 1.0 / 3.0 == 0.0
@public
def check_fail_0():
    pass


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: 1.0 / 3.0 * 3.0 == 1.0
@public
def check_fail_1():
    pass


@public
def div3():
    d: decimal = 1.0 / 3.0
    p: decimal = 10.0
    e: decimal = 0.0
    for i in range(10):
        e += 3.0 * 1.0 / p
        p *= 10.0
    
    assert d == e, UNREACHABLE
