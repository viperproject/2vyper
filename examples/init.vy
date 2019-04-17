
# Reward Payment

did_pay: bool
reward: wei_value

@public
def __init__(amount: wei_value):
	self.did_pay = False
	self.reward = amount