#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


self_address: address


#@ invariant: self.self_address == self


@public
def __init__():
    self.self_address = self


#@ ensures: implies(success(), result() == self)
@public
def get_self_address() -> address:
    return self


#@ ensures: self == old(self)
@public
def no_change():
    pass


#@ ensures: self == old(self)
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self != old(self)
@public
def change():
    self.self_address = ZERO_ADDRESS
