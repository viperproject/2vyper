#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Reward Payment

did_pay: bool
reward: wei_value

#:: Label(INV)
#@ invariant: implies(not self.did_pay, sum(sent()) == 0)
#:: Label(INVC)
#@ invariant: implies(self.did_pay, sum(sent()) == self.reward)

@public
@payable
def __init__():
   self.did_pay = False
   self.reward = msg.value / 2

#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, INVC)
@public
def claim_reward():
   if (not self.did_pay):
      # send reward to the caller
      #:: ExpectedOutput(call.invariant:assertion.false, INV)
      raw_call(msg.sender, b"", outsize=0, value=self.reward, gas=msg.gas)
      self.did_pay = True
