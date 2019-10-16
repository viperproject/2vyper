#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract E:
    def balance_of(a: address) -> wei_value: constant


i: int128
e: E


#:: Label(INV)
#@ invariant: self.i >= 0


@public
def __init__(_e: address):
    self.e = E(_e)


@public
def inc_i():
    self.i += 1


#@ ensures: self.i == old(self.i)
#@ ensures: self == old(self)
@public
def get_balance_of(a: address) -> wei_value:
    return self.e.balance_of(a)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self == old(self)
@public
def get_balance_of_fail(a: address) -> wei_value:
    ret: wei_value = self.e.balance_of(a)
    self.i = 32
    return ret


@public
def get_balance_of_call_fail(a: address) -> wei_value:
    self.i = -1
    #:: ExpectedOutput(call.invariant:assertion.false, INV)
    return self.e.balance_of(a)
