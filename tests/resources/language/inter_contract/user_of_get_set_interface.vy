#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import get_set_interface

#@ config: trust_casts

token: get_set_interface

# These variables are constant
#@ invariant: self.token == old(self.token)

#@ preserves:
    #@ always ensures: old(mapping(self.token)[self]) <= mapping(self.token)[self]

#:: Label(INV)
#@ inter contract invariant: old(mapping(self.token)[self]) <= mapping(self.token)[self]

@public
def __init__(a: address):
    self.token = get_set_interface(a)

@public
def foo():
    assert self.token.get() == 0
    #:: ExpectedOutput(during.call.invariant:assertion.false, INV)
    self.token.set(2)
