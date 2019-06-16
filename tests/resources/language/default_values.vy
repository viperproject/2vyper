#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

b: bool
i: int128
u: uint256

#@ invariant: not self.b
#@ invariant: self.i == 0

#:: ExpectedOutput(invariant.violated:assertion.false)
#@ invariant: self.u == 1

