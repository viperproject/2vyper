#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


bts: bytes[1024]


#@ ensures: len(self.bts) == 2 * len(b)
@public
def double(b: bytes[512]):
    self.bts = concat(b, b)


#@ ensures: len(self.bts) == 4 * len(b)
@public
def times4(b: bytes[1]):
    self.bts = concat(b, b, b, b)


#@ ensures: result() == concat(b, b, b, b, b)
@public
def times5(b: bytes[1]) -> bytes[5]:
    return concat(b, b, b, b, b)
