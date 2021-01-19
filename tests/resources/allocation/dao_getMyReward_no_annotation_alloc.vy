#:: ExpectedOutput(leakcheck.failed:allocation.leaked)
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

@private
def withdrawRewardFor(_account: address) -> bool:
    if (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply < self.paidOut[_account]:
        return False

    reward: uint256 = (self.balanceOf[_account] * self.accumulatedInput) / self.totalSupply - self.paidOut[_account]
    #:: ExpectedOutput(carbon)(call.leakcheck:allocation.leaked, INLINE) | ExpectedOutput(carbon)(payout.failed:no.performs, INLINE)
    send(_account, reward)
    self.paidOut[_account] += reward
    return True


#:: ExpectedOutput(leakcheck.failed:allocation.leaked)
@public
def getMyReward() -> bool:
    #:: Label(INLINE)
    return self.withdrawRewardFor(msg.sender)
