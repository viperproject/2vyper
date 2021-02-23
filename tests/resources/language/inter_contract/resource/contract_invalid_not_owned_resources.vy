#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

from . import interface_a1
from . import interface_a2
from . import interface_b
from . import interface_d

implements: interface_d

#@ invariant: forall({a: address}, allocated[interface_d.d](a) == 0)
#:: ExpectedOutput(invalid.program:invalid.resource)
#@ invariant: forall({a: address}, allocated[interface_b.b](a) == 0)

@public
def foo():
    pass
