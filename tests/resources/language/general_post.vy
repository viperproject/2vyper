#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

f: int128


#:: Label(CC)
#@ always ensures: self.f == old(self.f)


@public
def no_change():
    self.f = self.f


#:: ExpectedOutput(postcondition.violated:assertion.false, CC)
@public
def change():
    self.f += 1