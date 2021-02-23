#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import ghost_interface

implements: ghost_interface

#@ ghost:
    #@ @implements
    #:: ExpectedOutput(invalid.program:ghost.function.call)
    #@ def some() -> int128: 0 if accessible(self, self.balance) else 1


@public
def id(i: int128) -> int128:
    return i
