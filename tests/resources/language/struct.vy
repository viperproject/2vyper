#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


struct Rational:
    numerator: int128
    denominator: int128


struct Person:
    i: int128
    friends: int128[3]


@public
def __init__():
    pass


@public
def id(r: Rational) -> Rational:
    return r


#@ ensures: p.friends[0] == old(p.friends[0])
@public
def skip(p: Person):
    pass


@public
def is_friends_with(p: Person, q: Person) -> bool:
    for i in range(3):
        if p.friends[i] == q.i:
            return True
    return False


#@ ensures: implies(success(), result() == (p.i == q.i))
#@ ensures: implies(success(), implies(p.i == 5 and q.i == 6, not result()))
@public
def person_eq(p: Person, q: Person) -> bool:
    return p.i == q.i


#@ ensures: implies(success(), result().numerator == r.denominator)
#@ ensures: implies(success(), result().denominator == r.numerator)
@public
def invert(r: Rational) -> Rational:
    new_r: Rational = r
    new_r.numerator = r.denominator
    new_r.denominator = r.numerator
    return new_r
