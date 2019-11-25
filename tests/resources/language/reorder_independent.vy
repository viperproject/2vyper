#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: no_gas, no_overflows

val: int128


#@ ensures: reorder_independent(self.val)
@public
def set_val(new_val: int128):
    self.val = new_val


#@ ensures: reorder_independent(self.val)
@public
@payable
def set_val_msg():
    self.val = convert(as_unitless_number(msg.value), int128)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: reorder_independent(self.val)
@public
def inc_val():
    self.val += 1


#@ ensures: reorder_independent(result())
@public
def get_tx_origin() -> address:
    return tx.origin
