#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


ui: wei_value
mp: map(int128, wei_value)

#@ ensures: self.ui >= 0
@public
def simple():
    pass

#@ ensures: result() >= 0
@public
def calc() -> wei_value:
    return self.mp[100]

#@ ensures: result() >= 0
@public
def args(arg: wei_value) -> wei_value:
    return arg

#@ ensures: result() >= 0
@public
def _add(a: wei_value, b: wei_value) -> wei_value:
    return a + a + b + a + b

#@ ensures: success()
@public
def _div(a: wei_value, b: wei_value) -> uint256:
    return a / (b + 1)

#@ ensures: not success()
@public
def fail(a: wei_value, b: wei_value) -> wei_value:
    assert a > b
    self.ui = b - a
    return a

#@ ensures: result() == as_wei_value(i, "lovelace")
@public
def transform(i: int128) -> wei_value:
    return as_wei_value(i, "lovelace")
