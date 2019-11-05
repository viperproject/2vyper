#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: trust_casts

from . import constant_interface


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: storage(msg.sender) == old(storage(msg.sender))
@public
def set_val():
    constant_interface(msg.sender).set_value(42)


#@ ensures: storage(msg.sender) == old(storage(msg.sender))
@public
def do_nothing():
    constant_interface(msg.sender).change_nothing()
