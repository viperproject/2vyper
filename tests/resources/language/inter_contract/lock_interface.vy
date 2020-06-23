#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def mapping() -> map(address, bool): ...

#@ caller private: mapping(self)[caller()]

#@ ensures: success() ==> result() == mapping(self)[msg.sender]
@constant
@public
def get() -> bool:
    raise "Not implemented"

#@ ensures: success() ==> mapping(self)[msg.sender] == True
@public
def lock():
    raise "Not implemented"
