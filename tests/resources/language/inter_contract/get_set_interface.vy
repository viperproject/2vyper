#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def mapping() -> map(address, uint256): ...

#@ caller private: mapping(self)[caller()]

# This invariant is intentional commented out. The user of this interface should not be able to verify its properties.
# invariant: forall({a: address}, old(mapping(self)[a]) <= mapping(self)[a])

#@ ensures: success() ==> result() == mapping(self)[msg.sender]
@constant
@public
def get() -> uint256:
    raise "Not implemented"

#@ ensures: success() ==> mapping(self)[msg.sender] == val
@public
def set(val: uint256):
    raise "Not implemented"
