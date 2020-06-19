#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import interface_with_postcondition_conflicting_user

#@ config: trust_casts

token_A: interface_with_postcondition_conflicting_user

#@ preserves:
    #@ always ensures: mapping(self.token_A)[self] == 1
    # Conflicting post condition:
    #@ always ensures: old(mapping(self.token_A)[self]) == 1

# These variables are constant
#@ invariant: self.token_A == old(self.token_A)

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: revert()
@public
def __init__(token_A_address: address):
    self.token_A = interface_with_postcondition_conflicting_user(token_A_address)
    self.token_A.set(0)
    self.token_A.increase()
