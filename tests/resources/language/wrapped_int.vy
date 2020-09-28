#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: no_gas, no_overflows

N_COINS: constant(int128) = 2
A: constant(int128) = 42

t: uint256

@public
@payable
def __init__(arg: uint256):
    five: uint256 = 5
    six: uint256 = 6
    thirty: uint256 = five * six
    test1: uint256 = thirty * self.t
    test2: uint256 = self.t * self.t
    test3: uint256 = self.t * arg
    if test1 >= 30:
        assert self.t != 0, UNREACHABLE
        five = 5
    a: address = 0x000000001000000000010000000000000600000a
    b: address = 0x000000001000000000010000000000000600000a
    c: address = msg.sender
    test4: uint256 = 0
    for i in range(3):
        test4 += convert(i, uint256)
    assert test4 == 3, UNREACHABLE
    if self.t > 0:
        test5: uint256 = 0
        for i in [convert(5, uint256), test1, test2, test3, test4]:
            test6: uint256 = 0
            test5 += i
            test6 += i
        assert test5 > 33, UNREACHABLE

        test7: uint256 = 0
        for i in [True, False, (test5 > 33)]:
            if i:
                if (test5 > 33):
                    test7 += 1
        assert test7 == 2, UNREACHABLE


#@ ensures: success() ==> result() == 11
@private
@constant
def test() -> uint256:
    five: uint256 = 5
    six: uint256 = 6
    S: uint256 = 11

    Dprev: uint256 = 0
    D: uint256 = S
    Ann: uint256 = A * N_COINS
    for _i in range(2):
        D_P: uint256 = D
        #@ lemma_assert interpreted(D_P * D / (five * N_COINS + 1) == 11)
        D_P = D_P * D / (five * N_COINS + 1)  # +1 is to prevent /0
        #@ lemma_assert interpreted(D_P * D / (six * N_COINS + 1) == 9)
        D_P = D_P * D / (six * N_COINS + 1)  # +1 is to prevent /0
        Dprev = D
        #@ lemma_assert interpreted((Ann * S + D_P * N_COINS) * D / ((Ann - 1) * D + (N_COINS + 1) * D_P) == 11)
        D = (Ann * S + D_P * N_COINS) * D / ((Ann - 1) * D + (N_COINS + 1) * D_P)
        #@ lemma_assert D == 11
        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 1:
                break
        else:
            if Dprev - D <= 1:
                break
    return D

