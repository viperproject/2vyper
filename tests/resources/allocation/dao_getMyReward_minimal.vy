#@ config: allocation, no_performs

balanceOf: public(map(address, uint256))
paidOut: public(map(address, uint256))
totalSupply: uint256
accumulatedInput: uint256

#@ resource: token()

#@ invariant: allocated[token]() == self.balanceOf

@private
def withdrawRewardFor(_account: address) -> bool:
    if (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply < self.paidOut[_account]:
        return False

    reward: uint256 = (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply - self.paidOut[_account]
    send(_account, reward)
    self.paidOut[_account] += reward
    return True

@public
def getMyReward() -> bool:
    return self.withdrawRewardFor(msg.sender)

@private
def fixed_withdrawRewardFor(_account: address) -> bool:
    if (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply < self.paidOut[_account]:
        return False

    reward: uint256 = (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply - self.paidOut[_account]
    self.paidOut[_account] += reward
    send(_account, reward)
    return True

@public
def fixed_getMyReward() -> bool:
    return self.fixed_withdrawRewardFor(msg.sender)
