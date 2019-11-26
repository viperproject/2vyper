#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: a >= 0 ==> (a <= 0 ==> a == 0)
#@ ensures: a >= 0 ==> a <= 0 ==> a == 0
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: (a >= 0 ==> a <= 0) ==> a == 0
@public
def func(a: int128):
    pass


#@ ensures: b == 0 ==> revert()
#@ ensures: success() ==> result() == a / b
@public
def divide(a: int128, b: int128) -> int128:
    return a / b
