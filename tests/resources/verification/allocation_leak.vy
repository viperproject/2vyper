#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


b: bool
owner: address
value: wei_value


#:: Label(INV)
#@ invariant: self.b ==> forall({a: address}, {allocated(a)}, allocated(a) == (self.value if a == self.owner else 0))


#@ performs: payable(msg.value)
@public
@payable
def __init__():
    self.b = True
    self.owner = msg.sender
    self.value = msg.value


#@ performs: payable(msg.value)
#:: ExpectedOutput(leakcheck.failed:allocation.leaked)
@public
@payable
def always_fail():
    assert False


#@ performs: payable(msg.value)
#:: ExpectedOutput(leakcheck.failed:allocation.leaked) | ExpectedOutput(carbon)(invariant.violated:assertion.false, INV)
@public
@payable
def pay_fail():
    assert self.b
    assert msg.sender == self.owner


#@ performs: payout(self.value)
#:: ExpectedOutput(leakcheck.failed:allocation.leaked)
@public
def withdraw_fail():
    assert msg.sender == self.owner
    #:: ExpectedOutput(carbon)(call.leakcheck:allocation.leaked) | ExpectedOutput(carbon)(call.invariant:assertion.false, INV) | ExpectedOutput(carbon)(reallocate.failed:insufficient.funds)
    send(msg.sender, self.value)
