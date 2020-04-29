#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract C:
    def f(): modifying
    def c(): constant

@private
@constant
def noop():
    pass

#@ ensures: storage(self) == old(storage(self))
#@ ensures: storage(msg.sender) == old(storage(msg.sender))
#@ ensures: forall({a: address}, storage(a) == old(storage(a)))
@public
def change_nothing():
    C(msg.sender).c()
    self.noop()


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: storage(msg.sender) == old(storage(msg.sender))
@public
def change_nothing_fail():
    C(msg.sender).f()
