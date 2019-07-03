#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#:: Label(CONST_BALANCE)
#@ invariant: old(self.balance) == self.balance

#:: ExpectedOutput(invariant.violated:assertion.false, CONST_BALANCE)
@public
def foo():
    pass

#:: ExpectedOutput(invariant.violated:assertion.false, CONST_BALANCE)
@public
def bar():
    assert False
