#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import ghost_interface


ghost: ghost_interface


#@ ensures: _some_uval(self.ghost) >= 0
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: _some_val(self.ghost) >= 0
@public
def __init__():
    self.ghost = ghost_interface(msg.sender)
