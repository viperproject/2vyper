#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

a: int128

#@ pure
@private
@constant
def get_a() -> int128:
    return self.a

@public
def compliant():
    for i in range(5):
        #@ invariant: result(self.get_a()) >= old(result(self.get_a()))
        self.a += 1

@public
def not_compliant():
    for i in range(5):
        #:: ExpectedOutput(loop.invariant.not.preserved:assertion.false)
        #@ invariant: result(self.get_a()) >= old(result(self.get_a()))
        self.a = 1
