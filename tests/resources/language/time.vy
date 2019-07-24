#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


time: timestamp


#@ ensures: self.time == t
#@ ensures: t >= 0
@public
def set_time(t: timestamp):
    self.time = t


#@ ensures: self.time == old(self.time) + t
@public
def increase_time(t: timedelta):
    self.time += t


#@ ensures: self.time == block.timestamp
@public
def use_block():
    self.time = block.timestamp