#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Reward Payment

did_pay: bool
reward: wei_value

#@ invariant: forall({a: address}, {sent(a)}, {old(sent(a))}, old(sent(a)) <= sent(a))
#:: Label(INV)
#@ invariant: implies(not self.did_pay, self.balance >= self.reward)
#:: Label(INVC)
#@ invariant: implies(not self.did_pay, sum(sent()) == 0)
#:: Label(INVC2)
#@ invariant: implies(self.did_pay, sum(sent()) == self.reward)

@public
@payable
def __init__():
	self.did_pay = False
	self.reward = msg.value

@public
def claim_reward():
	if (not self.did_pay):
		# send reward to the caller
		self.did_pay = True
		send(msg.sender, self.reward)

#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, INVC2)
@public
def claim_reward_fail():
	if (not self.did_pay):
		# send reward to the caller
		#:: ExpectedOutput(call.invariant:assertion.false, INV) | ExpectedOutput(carbon)(call.invariant:assertion.false, INVC)
		send(msg.sender, self.reward)
		self.did_pay = True

@public
def claim_reward_raw():
	if (not self.did_pay):
		# send reward to the caller
		self.did_pay = True
		raw_call(msg.sender, b"", outsize=0, value=self.reward, gas=msg.gas)

#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, INVC2)
@public
def claim_reward__raw_fail():
	if (not self.did_pay):
		# send reward to the caller
		#:: ExpectedOutput(call.invariant:assertion.false, INV) | ExpectedOutput(carbon)(call.invariant:assertion.false, INVC)
		raw_call(msg.sender, b"", outsize=0, value=self.reward, gas=msg.gas)
		self.did_pay = True