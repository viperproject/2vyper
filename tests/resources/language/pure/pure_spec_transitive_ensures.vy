#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

a: int128

#@ preserves:
    #:: Label(TRANSITIVE_POST)
    #@ always ensures: result(self.get_a()) >= old(result(self.get_a()))

#@ pure
@private
@constant
def get_a() -> int128:
    return self.a

@public
def compliant():
    self.a += 1

#:: ExpectedOutput(postcondition.violated:assertion.false, TRANSITIVE_POST)
@public
def not_compliant():
    self.a = 1
