#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #:: ExpectedOutput(invalid.program:invalid.type)
    #@ def _totalSupply() -> int256: ...

@public
@payable
def buyTokens(_beneficiary: address) -> address:
    return _beneficiary
