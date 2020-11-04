#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: trust_casts

from . import interface_a1
from . import interface_a2
from . import interface_b

i: interface_b

@public
def foo():
    send(msg.sender, 0)
