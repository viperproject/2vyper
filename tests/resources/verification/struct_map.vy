#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


struct Person:
    name: string[100]
    age: uint256


people: map(address, Person)


#@ invariant: forall({a: address}, {self.people[a].age}, self.people[a].age >= old(self.people[a].age))


@public
def set_self(p: Person):
    assert p.age >= self.people[msg.sender].age
    self.people[msg.sender] = p


@public
def set_name(n: string[100]):
    self.people[msg.sender].name = n


@public
def set_age(a: uint256):
    assert a >= self.people[msg.sender].age
    self.people[msg.sender].age = a
