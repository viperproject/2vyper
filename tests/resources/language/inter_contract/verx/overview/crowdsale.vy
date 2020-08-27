#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: trust_casts

from . import escrow_interface

escrow: escrow_interface
raised: uint256(wei)
goal: constant(uint256) = 10000 * 10 ** 18
closeTime: timestamp
_init: bool

#@ invariant: self.closeTime == old(self.closeTime)
#@ invariant: self.raised >= old(self.raised)
#@ invariant: self.escrow == old(self.escrow)
#@ invariant: self.escrow != self
#@ invariant: old(self._init) ==> self._init

#@ inter contract invariant: self._init ==> owner(self.escrow) == self
#@ always ensures: success() ==> block.timestamp <= self.closeTime and self.raised < goal ==> open_state(self.escrow)
#@ always ensures: old(sum(deposits(self.escrow)) >= self.raised) ==> success() ==> success_state(self.escrow) ==> sum(deposits(self.escrow)) >= goal

@public
def __init__(a: address, _bidding_time: timedelta):
    assert not self._init
    assert self != a
    self.escrow = escrow_interface(a)
    self.raised = as_wei_value(0, "wei")
    self.closeTime = block.timestamp + _bidding_time
    assert self.escrow.is_open()
    assert self.escrow.get_owner() == self
    self._init = True


@public
@payable
def invest():
    assert self._init
    assert self.escrow.is_open()
    self.escrow.deposit(msg.sender, value=msg.value)
    self.raised += msg.value


@public
def close():
    assert self._init
    assert block.timestamp > self.closeTime or self.raised >= goal
    assert self.escrow.is_open()
    if self.raised >= goal:
        self.escrow.close()
    else:
        self.escrow.refund()
