#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Reward Payment

did_pay: bool
reward: wei_value


#@ invariant: implies(old(self.did_pay), self.did_pay)
#:: Label(INV1)
#@ invariant: implies(not self.did_pay, self.balance >= 2 * self.reward)
#@ invariant: implies(old(self.did_pay), self.balance >= old(self.balance))

#:: Label(INV2)
#@ invariant: implies(not self.did_pay, sum(sent()) == 0)
#:: Label(INV3)
#@ invariant: implies(self.did_pay, sum(sent()) == self.reward)


@public
@payable
def __init__():
   assert msg.value % 2 == 0
   self.did_pay = False
   self.reward = msg.value / 2


@public
def claim_reward():
   if (not self.did_pay):
      # send reward to the caller
      self.did_pay = True
      raw_call(msg.sender, b"", outsize=0, value=self.reward, gas=msg.gas)


#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, INV3)
@public
def claim_reward_fail():
   if (not self.did_pay):
      # send reward to the caller
      #:: ExpectedOutput(call.invariant:assertion.false, INV1) | ExpectedOutput(carbon)(call.invariant:assertion.false, INV2)
      raw_call(msg.sender, b"", outsize=0, value=self.reward, gas=msg.gas)
      self.did_pay = True
