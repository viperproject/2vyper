# @version 0.2.x

#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

event MyEvent:
    arg: uint256

@external
def normal() -> int128:
    log MyEvent(0)
    return 5