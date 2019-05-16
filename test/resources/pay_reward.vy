
# Reward Payment

did_pay: bool
reward: wei_value

#:: Label(INV)
#@ invariant: implies(not self.did_pay, self.balance >= self.reward)

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

@public
def claim_reward_fail():
	if (not self.did_pay):
		# send reward to the caller
		#:: ExpectedOutput(call.invariant:assertion.false, INV)
		send(msg.sender, self.reward)
		self.did_pay = True

@public
def claim_reward_raw():
	if (not self.did_pay):
		# send reward to the caller
		self.did_pay = True
		raw_call(msg.sender, b"", outsize=0, value=self.reward, gas=msg.gas)

@public
def claim_reward__raw_fail():
	if (not self.did_pay):
		# send reward to the caller
		#:: ExpectedOutput(call.invariant:assertion.false, INV)
		raw_call(msg.sender, b"", outsize=0, value=self.reward, gas=msg.gas)
		self.did_pay = True