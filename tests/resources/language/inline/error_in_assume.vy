#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ ensures: True
@private
@constant
def foo():
    assert False

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success(if_not=out_of_gas)
@public
def bar(val: int128):
    self.foo()
