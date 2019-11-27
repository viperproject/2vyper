#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


bb100: bytes[100]


#@ ensures: len(self.bb100) <= 100
@public
def get_bb100() -> bytes[100]:
    return self.bb100


#@ ensures: len(self.bb100) == 3
@public
def set_bb100():
    self.bb100 = b"abc"


#@ ensures: len(result()) == 0
@public
def empty() -> bytes[5]:
    return b""