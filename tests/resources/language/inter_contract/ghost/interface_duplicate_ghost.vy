#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import interface_a1

#@ interface

#@ ghost:
    #@ def a() -> int128: ...

#@ ensures: a(self) == 42
@public
def foo():
    raise "Not implemented"
