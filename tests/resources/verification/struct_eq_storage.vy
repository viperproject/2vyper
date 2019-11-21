#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

struct Person:
    age: uint256
    _name: string[100]
    money: int128


name: string[100]
p: Person

#:: Label(PCONST)
#@ invariant: self.p == old(self.p)


@public
def __init__():
    self.p = Person({age: 12, _name: "Anakin", money: 0})


#@ ensures: storage(self) == old(storage(self))
@public
def no_change():
    pass


#@ ensures: storage(self) == old(storage(self))
@public
def no_effective_change():
    old_name: string[100] = self.name
    self.name = "Hello World!"
    self.name = old_name


#@ ensures: storage(self) == old(storage(self))
@public
def no_effective_changes():
    old_name: string[100] = self.name
    self.name = "Hello World!"
    self.name = "Hello Africa!"
    self.name = "Hello Antarctica!"
    self.name = "Hello America!"
    self.name = "Hello Australia!"
    self.name = "Hello Asia!"
    self.name = "Hello Europe??"
    self.name = old_name


#@ ensures: storage(self) == old(storage(self))
@public
def struct_no_effective_changes():
    assert self.p.age == 12 and self.p.money == 0
    old_name: string[100] = self.p._name
    self.p.age = 13
    self.p.age = 14
    self.p._name = "Anakin Skywalker"
    self.p.money = -1
    self.p.age = 15
    self.p._name = "Anakin"
    self.p.money = -12
    self.p.money = 0
    self.p.age = 12
    self.p._name = old_name


#:: ExpectedOutput(invariant.violated:assertion.false, PCONST)
@public
def change_fail():
    self.p.age = 13


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: storage(self) == old(storage(self))
@public
def self_change_fail():
    self.name = "Luke Skywalker"


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: storage(self) == old(storage(self))
@public
def changes_fail():
    self.p.age = 13
    self.p.age = 14
    self.p._name = "Anakin Skywalker"
    self.p.money = -1
    self.p.age = 15
    self.p._name = "Anakin"
    self.p.money = -12
    self.p.money = 0
    self.p.age = 12
