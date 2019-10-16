#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas, no_overflows


money: wei_value


#@ invariant: self.money <= self.balance


#@ ensures: self.balance == old(self.balance)
@public
def get_balance() -> wei_value:
    return self.balance


#@ ensures: self.balance == old(self.balance) + msg.value
@public
@payable
def pay():
    self.money += msg.value