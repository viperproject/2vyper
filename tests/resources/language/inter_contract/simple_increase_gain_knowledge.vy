#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def mapping() -> map(address, uint256): ...

#@ invariant: mapping(self)[ZERO_ADDRESS] == 0
#@ invariant: mapping(self)[0x000000001000000000010000000000000600000a] == 0
#@ invariant: forall({a: address}, mapping(self)[a] >= old(mapping(self)[a]))

#@ caller private: mapping(self)[caller()]

#@ ensures: success() ==> old(mapping(self)[msg.sender]) + 1 == mapping(self)[msg.sender]
@public
def increase() -> bool:
    raise "Not implemented"

#@ ensures: success() ==> result() == mapping(self)[msg.sender]
@public
@constant
def get() -> uint256:
    raise "Not implemented"
