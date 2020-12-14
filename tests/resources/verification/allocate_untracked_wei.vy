#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation

#@ invariant: forall({a: address}, allocated(a) == 0)
#@ invariant: sum(allocated()) == 0

#@ performs: payout(self.balance)
#@ performs: allocate_untracked[wei](msg.sender)
@public
def destroy():
    #@ allocate_untracked[wei](msg.sender)
    selfdestruct(msg.sender)

#@ performs: payout(self.balance)
@public
def destroy_no_perform():
    #:: ExpectedOutput(allocate.untracked.failed:no.performs)
    #@ allocate_untracked[wei](msg.sender)
    selfdestruct(msg.sender)

#@ performs: payout(self.balance)
@public
def destroy_fail():
    #:: ExpectedOutput(reallocate.failed:insufficient.funds)
    selfdestruct(msg.sender)
