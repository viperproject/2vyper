#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import issue006a

implements: issue006a


total_supply: uint256


#@ ghost:
    #@ @implements
    #@ def _totalSupply() -> uint256: self.total_supply


#:: ExpectedOutput(postcondition.not.implemented:assertion.false)
@public
@payable
def total() -> uint256:
    return 15
