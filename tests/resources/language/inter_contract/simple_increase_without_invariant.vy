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

#@ ensures: success() ==> old(mapping(self)[msg.sender]) + 1 == mapping(self)[msg.sender]
@public
def increase() -> bool:
    raise "Not implemented"

#@ ensures: success() ==> result() == mapping(self)[msg.sender]
@public
@constant
def get() -> uint256:
    raise "Not implemented"
