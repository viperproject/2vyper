#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

val: int128


#:: Label(POS) | ExpectedOutput(invariant.violated:assertion.false)
#@ invariant: self.val > 0


@public
def __init__():
    pass


#:: ExpectedOutput(invariant.violated:assertion.false, POS)
@public
def fail():
    self.val = -1
