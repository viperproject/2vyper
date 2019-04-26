
# Reward Payment

did_pay: bool
reward: wei_value

#@ invariant: self.did_pay == (self.reward == 0)

@public
def __init__(amount: wei_value):
	self.did_pay = False
	self.reward = amount

	if self.reward == 0:
		self.did_pay = True


@public
def pay_reward():
	self.did_pay = True
	self.reward = 0