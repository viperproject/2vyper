#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import interface


i: interface


@public
def __init__():
    self.i = interface(msg.sender)


#@ ensures: implies(success() and implements(self.i, interface), result() == val)
@public
def get_foo(val: int128) -> int128:
    return self.i.foo(val)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() == val)
@public
def get_foo_fail(val: int128) -> int128:
    return self.i.foo(val)