#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import interface

implements: interface

mp: map(int128, int128)

#@ ghost:
    #@ @implements
    #@ def _mapval(j: int128) -> int128: self.mp[j]

#@ lemma_def _mapval():
    #:: ExpectedOutput(invalid.program:invalid.lemma)
    #@ _mapval(0x000000001000000000010000000000000600000a, 0) == _mapval(0x000000001000000000010000000000000600000a, 0)


@public
def foo():
    pass
