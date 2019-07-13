#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


CC: constant(int128) = 50


struct Large:
    a00: int128
    a01: int128
    a02: int128
    a03: int128
    a04: int128
    a05: int128
    a06: int128
    a07: int128
    a08: int128
    a09: int128
    a10: int128
    a11: int128
    a12: int128
    a13: int128
    a14: int128
    a15: int128
    a16: int128
    a17: int128
    a18: int128
    a19: int128
    a20: int128
    a21: int128
    a22: int128
    a23: int128
    a24: int128
    a25: int128
    a26: int128
    a27: int128
    a28: int128
    a29: int128
    a30: int128


#@ ensures: implies(success(), result().a00 == l.a00 + CC)
#@ ensures: implies(success(), result().a00 == result().a01 - result().a02)
#@ ensures: implies(success(), implies(l.a05 > 0, result().a05 == CC * l.a05 + CC))
@public
def test0(l: Large) -> Large:
    new_l: Large = l
    new_l.a05 = 0
    for i in range(CC):
        new_l.a00 = new_l.a00 + 1
        new_l.a01 = new_l.a00 + new_l.a02
        new_l.a04 = new_l.a04 + new_l.a02 + new_l.a00 + 3
        if l.a05 > 0:
            new_l.a05 = new_l.a05 + l.a05 + 1
    return new_l