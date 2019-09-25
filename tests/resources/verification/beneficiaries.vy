#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract Client:
   def pay(): modifying


to_pay: map(address, wei_value)


#:: Label(SUM)
#@ invariant: sum(self.to_pay) <= self.balance
#@ invariant: forall({a: address}, self.to_pay[a] <= old(self.to_pay[a]))


@public
@payable
def __init__(beneficiaries: address[5]):
    assert msg.value % 5 == 0
    for i in range(5):
        self.to_pay[beneficiaries[i]] = msg.value / 5


@public
def withdraw():
    amount: wei_value = self.to_pay[msg.sender]
    self.to_pay[msg.sender] = 0
    Client(msg.sender).pay(value=amount)


@public
def withdraw_fail():
    #:: ExpectedOutput(call.invariant:assertion.false, SUM)
    Client(msg.sender).pay(value=self.to_pay[msg.sender])
    self.to_pay[msg.sender] = 0
