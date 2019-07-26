#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


time: timestamp


#@ invariant: self.time >= 0


@public
def __init__():
    self.time = block.timestamp


@public
def update_time():
    self.time = block.timestamp
