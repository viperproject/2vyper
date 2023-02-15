#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

from . import interface

i: interface
m: map(address, uint256)

#@ derived resource: token() -> interface.r[self.i]

#@ invariant: self.i == old(self.i)
#@ invariant: allocated[token]() == self.m

@public
def foo():
    self.i.foo()

#@ performs: payable[token](1)
@public
def create_test():
    self.m[msg.sender] += 1
    self.i.create_r()

#@ performs: payable[token](1)
#@ performs: create[interface.r[self.i]](1, to=self, actor=self)
@public
def create_test_with_redeclare():
    self.m[msg.sender] += 1
    self.i.create_r()

#@ performs: payable[token](1)
#@ performs: create[interface.r[self.i]](1, to=self, actor=self)
#@ performs: allow_to_liquidate[token](1, msg.sender)
#@ performs: payout[token](1)
#@ performs: reallocate[interface.r[self.i]](1, to=msg.sender, actor=self)
@public
def reallocate_test():
    assert self.i != self and self != msg.sender

    self.m[msg.sender] += 1
    self.i.create_r()
    #@ allow_to_liquidate[token](1, msg.sender)
    self.m[msg.sender] -= 1
    self.i.reallocate_r(msg.sender)

