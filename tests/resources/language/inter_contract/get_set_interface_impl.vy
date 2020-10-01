#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
from . import get_set_interface

implements: get_set_interface

amounts: map(address, uint256)

#@ ghost:
    #@ @implements
    #@ def mapping() -> map(address, uint256): self.amounts

@constant
@public
def get() -> uint256:
    return self.amounts[msg.sender]

@public
def set(val: uint256):
    self.amounts[msg.sender] = val + 1
    raw_call(0x000000001000000000010000000000000600000a, b"", outsize=128, gas=0)
    self.amounts[msg.sender] = val
