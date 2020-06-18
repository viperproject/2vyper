#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def getval() -> int128: ...

#@ invariant: getval(self) == 42

#@ ensures: success() ==> result() == getval(self)
@public
def get() -> int128:
    raise "Not implemented"
