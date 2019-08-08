#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
def times(a: decimal, b: decimal) -> decimal:
    return a * b


#@ ensures: implies(success(), result() >= a)
@public
def ipow2(a: int128) -> int128:
    return a * a


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() >= a)
@public
def dpow2(a: decimal) -> decimal:
    return a * a


#@ ensures: 2.0 / 2.0 == 1.0
#@ ensures: 0.0 < 1.0 / 2.0 and 1.0 / 2.0 < 1.0
#@ ensures: 2.0 + 1.0 / 2.0 - 3.0 / 2.0 == 1.0
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
