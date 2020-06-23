#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import interface

a: interface

#@ invariant: self.a == old(self.a)

@public
def __init__(address_a: address):
    self.a = interface(address_a)

#@ ensures: success() and implements(self.a, interface) ==> result() == 42
@public
def foo() -> int128:
    return self.a.get()
