#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import ghost_interface


#@ config: trust_casts


ghost: ghost_interface


@public
def __init__():
    self.ghost = ghost_interface(msg.sender)


#@ ensures: _some_uval(self.ghost) >= 0
#@ ensures: len(_some_uarr(self.ghost)) == 5
#@ ensures: _some_uarr(self.ghost)[4] >= 0
@public
def check():
    pass


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: _some_val(self.ghost) >= 0
@public
def check0_fail():
    pass


#:: ExpectedOutput(not.wellformed:seq.index.length)
#@ ensures: _some_uarr(self.ghost)[5] >= 0
@public
def check1_fail():
    pass
