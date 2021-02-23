# @version 0.2.4

#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


#@ ensures: result() == 5
@external
def normal() -> int128:
    return 5

#@ ensures: result() == 0
@external
def in_loop() -> int128:
    for i in range(3):
        return i
    
    return -1

@external
def no_val():
    return
