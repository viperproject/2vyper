#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import issue020b

implements: issue020b

#@ ghost:
    #@ @implements
    #@ def getval() -> int128: 42

@public
def get() -> int128:
    return 42
