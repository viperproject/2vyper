#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import ghost_interface


#@ config: trust_casts


ghost: ghost_interface


#:: ExpectedOutput(invariant.violated:assertion.false)
#@ invariant: _some_val(self.ghost) == old(_some_val(self.ghost))


@public
def __init__():
    self.ghost = ghost_interface(msg.sender)
