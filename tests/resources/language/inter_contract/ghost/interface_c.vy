#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from .subdir import interface_a2

#@ interface

#@ ghost:
    #@ def c() -> int128: ...
    #@ def owner() -> address: ...


#@ inter contract invariant: a(owner(self)) == 42

@public
def foo():
    raise "Not implemented"
