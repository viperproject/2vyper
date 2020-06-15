#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import simple_increase_gain_knowledge

implements: simple_increase_gain_knowledge

amounts: map(address, uint256)

#@ ghost:
    #@ @implements
    #@ def mapping() -> map(address, uint256): self.amounts

@public
def increase() -> bool:
    assert msg.sender != 0x000000001000000000010000000000000600000a
    self.amounts[msg.sender] += 1
    return True

@public
@constant
def get() -> uint256:
    return self.amounts[msg.sender]
