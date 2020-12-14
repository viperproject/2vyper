#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

#@ invariant: sum(allocated()) == 0

#@ performs: payable(msg.value)
#@ performs: payout(msg.value)
@public
@payable
def create_new_with_msg_value(at: address) -> address:
    new: address = create_forwarder_to(at, value=msg.value)
    return new

#@ performs: payout(self.balance)
#@ performs: allocate_untracked[wei](msg.sender)
@public
def create_new_with_whole_allocated_balance(at: address) -> address:
    #@ allocate_untracked[wei](msg.sender)
    new: address = create_forwarder_to(at, value=self.balance)
    return new

#@ performs: payout(self.balance)
@public
def create_new_with_whole_balance(at: address) -> address:
    #:: ExpectedOutput(reallocate.failed:insufficient.funds)
    new: address = create_forwarder_to(at, value=self.balance)
    return new
