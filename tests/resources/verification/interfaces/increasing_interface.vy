#
# Copyright (c) 2021 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def mapping() -> map(address, uint256): ...

#@ caller private increasing: mapping(self)[caller()]

@public
def mint():
    raise "Not implemented"


@public
def transfer():
    raise "Not implemented"