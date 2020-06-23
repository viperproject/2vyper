#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import lock_interface

#@ config: trust_casts

lock_A: lock_interface
lock_B: lock_interface

#@ preserves:
    #@ always ensures: mapping(self.lock_A)[self]
    #:: ExpectedOutput(postcondition.violated:assertion.false)
    #@ always ensures: mapping(self.lock_B)[self]

# These variables are constant
#@ invariant: self.lock_A == old(self.lock_A)
#@ invariant: self.lock_B == old(self.lock_B)

@public
def __init__(lock_A_address: address , lock_B_address: address):
    self.lock_A = lock_interface(lock_A_address)
    self.lock_B = lock_interface(lock_B_address)
    assert not self.lock_A.get()
    assert not self.lock_B.get()
    self.lock_A.lock()
