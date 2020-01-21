#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

amount: public(uint256(wei))

#:: ExpectedOutput(invalid.program:wrong.type)
#@ invariant: sent() == self.amount

@public
@payable
def buyTokens(_beneficiary: address) -> address:
    return _beneficiary
