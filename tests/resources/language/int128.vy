#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas, no_overflows

#@ requires: b == c + d
#@ lemma_def distributive(a: int128, b: int128, c: int128, d: int128):
    #@ a * b == a * c + a * d

#@ lemma_def mul_recursive_step(i: int128, j: int128):
    #@ lemma.distributive(i, j, j - 1, 1)
    #@ lemma.distributive(j, i, i - 1, 1)

#@ lemma_def mul_sign(i: int128, j: int128):
    #@   i  *   j  == (-i) * (-j)
    #@ (-i) *   j  ==   i  * (-j)
    #@ (-i) *   j  == -(i  *   j)
    #@   i  * (-j) == -(i  *   j)


#@ ensures: a ==  4 and b ==  2 ==> result() ==  6
#@ ensures: a ==  4 and b == -2 ==> result() ==  2
#@ ensures: a == -4 and b ==  2 ==> result() == -2
#@ ensures: a == -4 and b == -2 ==> result() == -6
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: a == -4 and b == -2 ==> result() ==  6
@public
def _add(a: int128, b: int128) -> int128:
    return a + b


#@ ensures: a ==  4 and b ==  2 ==> result() ==  2
#@ ensures: a ==  4 and b == -2 ==> result() ==  6
#@ ensures: a == -4 and b ==  2 ==> result() == -6
#@ ensures: a == -4 and b == -2 ==> result() == -2
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: a == -4 and b == -2 ==> result() ==  2
@public
def _sub(a: int128, b: int128) -> int128:
    return a - b


#@ ensures: a ==  4 and b ==  2 ==> result() ==  8
#@ ensures: a ==  4 and b == -2 ==> result() == -8
#@ ensures: a == -4 and b ==  2 ==> result() == -8
#@ ensures: a == -4 and b == -2 ==> result() ==  8
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: a == -4 and b == -2 ==> result() == -8
@public
def _mul(a: int128, b: int128) -> int128:
    # Some lemmas are needed
    #@ lemma_assert lemma.mul_sign(a, b)
    #@ lemma_assert lemma.mul_recursive_step(a, b)
    return a * b


#@ ensures: a ==  4 and b ==  2 ==> result() ==  2
#@ ensures: a ==  4 and b == -2 ==> result() == -2
#@ ensures: a == -4 and b ==  2 ==> result() == -2
#@ ensures: a == -4 and b == -2 ==> result() ==  2
#@ ensures: a ==  4 and b ==  3 ==> result() ==  1
#@ ensures: a == -4 and b ==  3 ==> result() == -1
#@ ensures: a == -4 and b == -3 ==> result() ==  1
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: a == -4 and b == -2 ==> result() == -2
@public
def _div(a: int128, b: int128) -> int128:
    # Some lemmas are needed
    #@ lemma_assert 2 / 2 == 1
    #@ lemma_assert 4 / 2 == 2
    #@ lemma_assert 1 / 3 == 0
    #@ lemma_assert 3 / 3 == 1
    #@ lemma_assert 4 / 3 == 1
    return a / b


#@ ensures: a ==  4 and b ==  2 ==> result() ==  0
#@ ensures: a ==  4 and b == -2 ==> result() ==  0
#@ ensures: a == -4 and b ==  2 ==> result() ==  0
#@ ensures: a == -4 and b == -2 ==> result() ==  0
#@ ensures: a ==  4 and b ==  3 ==> result() ==  1
#@ ensures: a ==  4 and b == -3 ==> result() ==  1
#@ ensures: a == -4 and b ==  3 ==> result() == -1
#@ ensures: a == -4 and b == -3 ==> result() == -1
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: a == -4 and b == -2 ==> result() == -2
@public
def _mod(a: int128, b: int128) -> int128:
    # Some lemmas are needed
    #@ lemma_assert 2 % 2 == 0
    #@ lemma_assert 4 % 2 == 0
    #@ lemma_assert -4 % 2 == 0
    #@ lemma_assert 1 % 3 == 1
    #@ lemma_assert 3 % 3 == 0
    #@ lemma_assert 4 % 3 == 1
    #@ lemma_assert -4 % 3 == -1
    return a % b


#@ ensures: forall({a: int128, b: int128}, b != 0 and a % b == 0 ==> a / b * b == a)
#@ ensures: forall({a: int128, b: int128}, b != 0 ==> a / b * b + a % b == a)
@public
def check():
    pass
