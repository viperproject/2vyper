#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ invariant: forall({x: wei_value}, x >= 0)


#@ ensures: forall({x: wei_value}, x >= 0)
#@ ensures: forall({x: int128[5]}, x[4] >= 0 or x[4] <= 0)
#@ ensures: forall({x: map(int128, map(int128, wei_value))}, x[5][3] >= 0)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: forall({x: wei_value}, x <= 42)
@public
def check():
    pass
