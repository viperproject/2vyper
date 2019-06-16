#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

ss: string[5]


#@ invariant: len(self.ss) == 5


@public
def set_ss(new_ss: string[5]):
    self.ss = new_ss
    self.ss = "asdfg"


#@ ensures: len(self.ss) == 5
@public
def get_ss() -> string[6]:
    return self.ss


#@ ensures: len(result()) == 0
@public
def empty() -> string[5]:
    return ""