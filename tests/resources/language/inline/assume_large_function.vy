#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Verification took   2.86 seconds. [benchmark=10] (With assume_private_function)
# Verification took 645.44 seconds. [benchmark=3]  (With inline)

N_COINS: constant(int128) = 2
A: constant(int128) = 42

#@ ensures: success() ==> result() == a * b + 11.0
@private
@constant
def times_plus_some_val(a: decimal, b: decimal) -> decimal:
    five: uint256 = 5
    six: uint256 = 6
    xp: uint256[N_COINS] = [five, six]
    S: uint256 = 0
    for _x in xp:
        S += _x

    Dprev: uint256 = 0
    D: uint256 = S
    Ann: uint256 = A * N_COINS
    for _i in range(2): # This was 255
        D_P: uint256 = D
        for _x in xp:
            D_P = D_P * D / (_x * N_COINS + 1)  # +1 is to prevent /0
        Dprev = D
        D = (Ann * S + D_P * N_COINS) * D / ((Ann - 1) * D + (N_COINS + 1) * D_P)
        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 1:
                break
        else:
            if Dprev - D <= 1:
                break
    x: decimal = 0.0
    y: decimal = 1.0
    return a * b * y + x + convert(D, decimal)

#@ ensures: success() ==> a == 53.0
@public
@constant
def call1():
    a: decimal = 0.0
    a = self.times_plus_some_val(6.0, 7.0)

#@ ensures: success() ==> a == 53.0
@public
@constant
def call2():
    a: decimal = 0.0
    a = self.times_plus_some_val(6.0, 7.0)
