#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
def test_convert():
    u: uint256 = 2
    i: int128 = 2
    d: decimal = 2.0
    e: decimal = 2.0 + 7.0 / 10.0 + 1.0 / 100.0
    z: int128 = 0

    assert convert(u, int128) == i, UNREACHABLE
    assert convert(i, uint256) == u, UNREACHABLE

    assert convert(True, uint256) == 1, UNREACHABLE
    assert convert(False, uint256) == 0, UNREACHABLE

    assert convert(True, int128) == 1, UNREACHABLE
    assert convert(False, int128) == 0, UNREACHABLE

    assert convert(True, decimal) == 1.0, UNREACHABLE
    assert convert(False, decimal) == 0.0, UNREACHABLE

    assert convert(3, bool) == True, UNREACHABLE
    assert convert(u, bool) == True, UNREACHABLE
    assert convert(i, bool) == True, UNREACHABLE
    assert convert(d, bool) == True, UNREACHABLE

    assert convert(0, bool) == False, UNREACHABLE
    assert convert(0.0, bool) == False, UNREACHABLE
    assert convert(z, bool) == False, UNREACHABLE

    assert convert(u, decimal) == d, UNREACHABLE
    assert convert(d, int128) == i, UNREACHABLE
    assert convert(d, uint256) == u, UNREACHABLE

    assert convert(e, int128) == i, UNREACHABLE
    assert convert(-e, int128) == -i, UNREACHABLE

    #:: ExpectedOutput(assert.failed:assertion.false)
    assert convert(i, uint256) == u + 1, UNREACHABLE


#@ ensures: implies(i < 0, revert())
@public
def test_convert_revert(i: int128):
    u: uint256 = convert(i, uint256)


#@ ensures: implies(u >= 170141183460469231731687303715884105728, revert())
@public
def test_convert_overflow(u: uint256):
    i: int128 = convert(u, int128)


#@ ensures: implies(u >= 170141183460469231731687303715884105728, revert())
@public
def test_convert_decimal_overflow(u: uint256):
    d: decimal = convert(u, decimal)


#@ ensures: forall({i: int128}, implies(i != 0, convert(i, bool)))
#@ ensures: not convert(0, bool)
#@ ensures: forall({i: int128}, convert(convert(i, decimal), int128) == i)
@public
def check():
    pass
