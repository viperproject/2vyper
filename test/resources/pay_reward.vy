#:: IgnoreFile(0)
# Reward Payment

did_pay: bool
reward: wei_value

@public
def __init__(amount: wei_value):
	self.did_pay = False
	self.reward = amount

@public
def claim_reward():
	if (not self.did_pay):
		# send reward to the caller
		raw_call(msg.sender, b"", outsize=0, 
			value=self.reward, gas=msg.gas)
		self.did_pay = True