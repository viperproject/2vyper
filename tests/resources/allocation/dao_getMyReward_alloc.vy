#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

balanceOf: public(map(address, uint256))
paidOut: public(map(address, uint256))
totalSupply: uint256
accumulatedInput: uint256

#@ resource: token()

#@ invariant: allocated[token]() == self.balanceOf
#@ invariant: sum(self.balanceOf) == self.totalSupply

#:: Label(INV)
#@ invariant: forall({a: address}, allocated(a) == (0 if self.totalSupply == 0 else(self.balanceOf[a] * self.accumulatedInput) / self.totalSupply - self.paidOut[a]))


@private
def withdrawRewardFor(_account: address) -> bool:
    if (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply < self.paidOut[_account]:
        return False

    reward: uint256 = (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply - self.paidOut[_account]
    #:: ExpectedOutput(call.invariant:assertion.false, INLINE, INV)
    send(_account, reward)
    self.paidOut[_account] += reward
    return True


#@ performs: payout(0 if self.totalSupply == 0 else
    #@ (self.balanceOf[msg.sender] * self.accumulatedInput) / self.totalSupply - self.paidOut[msg.sender])
#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, INV)
@public
def getMyReward() -> bool:
    #:: Label(INLINE)
    return self.withdrawRewardFor(msg.sender)


@private
def fixed_withdrawRewardFor(_account: address) -> bool:
    if (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply < self.paidOut[_account]:
        return False

    reward: uint256 = (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply - self.paidOut[_account]
    self.paidOut[_account] += reward
    send(_account, reward)
    return True


#@ performs: payout(0 if self.totalSupply == 0 else
    #@ (self.balanceOf[msg.sender] * self.accumulatedInput) / self.totalSupply - self.paidOut[msg.sender])
@public
def fixed_getMyReward() -> bool:
    return self.fixed_withdrawRewardFor(msg.sender)
