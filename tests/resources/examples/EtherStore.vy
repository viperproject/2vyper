
# Taken from https://hackernoon.com/hackpedia-16-solidity-hacks-vulnerabilities-their-fixes-and-real-world-examples-f3210eba5148


WEEK: constant(timedelta) = 3600 * 24 * 7


withdrawalLimit: public(wei_value)
lastWithdrawTime: public(map(address, timestamp))
balances: public(map(address, wei_value))


#:: Label(BB)
#@ invariant: self.balance >= sum(self.balances)


@public
def __init__():
    self.withdrawalLimit = as_wei_value(1, "ether")


@public
@payable
def depositFunds():
    self.balances[msg.sender] += msg.value


@public
def withdrawFunds(_weiToWithdraw: wei_value):
    assert self.balances[msg.sender] >= _weiToWithdraw
    # limit the withdrawal
    assert _weiToWithdraw <= self.withdrawalLimit
    # limit the time allowed to withdraw
    assert block.timestamp >= self.lastWithdrawTime[msg.sender] + WEEK
    #:: ExpectedOutput(call.invariant:assertion.false, BB)
    raw_call(msg.sender, b"", outsize=0, value=_weiToWithdraw, gas=msg.gas)
    self.balances[msg.sender] -= _weiToWithdraw
    self.lastWithdrawTime[msg.sender] = block.timestamp
