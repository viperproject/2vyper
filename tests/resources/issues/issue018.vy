#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

@private
@constant
def times(a: decimal, b: decimal) -> decimal:
    x: decimal = 0.0
    y: decimal = 1.0
    return a * b * y + x

#@ ensures: a == 42.0
@public
@constant
def argument_name_equal():
    a: decimal = 0.0
    a = self.times(6.0, 7.0)

#@ ensures: c == 42.0
@public
@constant
def var_name_equal():
    c: decimal = 0.0
    x: decimal = 1.0
    c = self.times(6.0, 7.0) * x

#@ ensures: a == 42.0
@public
@constant
def var_and_argument_name_equal():
    a: decimal = 0.0
    x: decimal = 1.0
    a = self.times(6.0, 7.0) * x
