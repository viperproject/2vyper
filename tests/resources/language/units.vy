#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


units: {
    u: "unit"
}


iu: int128(u)
uu: uint256(u)

ius: int128(u)[9]
uus: uint256(u)[9]


#@ ensures: result() == a
@public
def test(a: int128(u), b: uint256(u)) -> int128(u):
    c: int128(u) = a
    d: int128(u**2) = c * a
    c = 12
    return a
