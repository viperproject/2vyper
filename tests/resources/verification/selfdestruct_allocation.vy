#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation, no_performs


balance_of: map(address, uint256(wei))


#:: Label(INV)
#@ invariant: allocated() == self.balance_of


@public
@payable
def deposit():
    self.balance_of[msg.sender] += msg.value


#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, INV)
@public
def destroy():
    #:: ExpectedOutput(reallocate.failed:insufficient.funds)
    selfdestruct(msg.sender)
