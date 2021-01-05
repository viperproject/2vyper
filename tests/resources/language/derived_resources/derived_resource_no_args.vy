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
#@ invariant: allocated[token]() == self.m#

@public
def foo():
    self.i.foo()

@public
def create_test():
    self.m[msg.sender] += 1
    self.i.create_r()

#@ performs: payout[token](1)
#@ performs: allow_to_decompose[token](1, msg.sender)
@public
def reallocate_test():
    self.m[msg.sender] += 1
    self.i.create_r()
    #@ allow_to_decompose[token](1, msg.sender)
    self.m[msg.sender] -= 1
    self.i.reallocate_r()

