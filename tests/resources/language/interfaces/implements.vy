#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import interface
from . import simple


i: interface
s: simple


#@ invariant: self.i == old(self.i)
#@ invariant: self.s == old(self.s)


@public
def __init__():
    self.i = interface(msg.sender)
    self.s = simple(msg.sender)


#@ ensures: implies(success() and implements(self.i, interface), result() == val)
@public
def get_foo(val: int128) -> int128:
    return self.i.foo(val)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() == val)
@public
def get_foo_fail(val: int128) -> int128:
    return self.i.foo(val)


#@ ensures: implies(success() and implements(self.s, simple), result() == new_val)
@public
def set_simple_val(new_val: int128) -> int128:
    self.s.set_val(new_val)
    return self.s.get_val()


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() == new_val)
@public
def set_simple_val_fail(new_val: int128) -> int128:
    self.s.set_val(new_val)
    return self.s.get_val()
