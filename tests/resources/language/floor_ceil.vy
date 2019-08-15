#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: implies(success(), result() == floor(d))
@public
def f(d: decimal) -> int128:
    return floor(d)


#@ ensures: implies(success(), result() == ceil(d))
@public
def c(d: decimal) -> int128:
    return ceil(d)


#@ ensures: floor(2.0) == 2
#@ ensures: floor(5.0 / 3.0) == 1
#@ ensures: floor(0.0) == 0
#@ ensures: floor(-0.0) == 0
#@ ensures: floor(-2.0) == -2
#@ ensures: floor(-5.0 / 3.0) == -2
#@ ensures: floor(5.0 / -3.0) == -2
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: floor(-5.0 / 3.0) == -1
@public
def checkf(d: decimal):
    pass


#@ ensures: ceil(2.0) == 2
#@ ensures: ceil(5.0 / 3.0) == 2
#@ ensures: ceil(0.0) == 0
#@ ensures: ceil(-0.0) == 0
#@ ensures: ceil(-2.0) == -2
#@ ensures: ceil(-5.0 / 3.0) == -1
#@ ensures: ceil(5.0 / -3.0) == -1
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: ceil(-5.0 / 3.0) == -2
@public
def checkc(d: decimal):
    pass
