#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#:: ExpectedOutput(invalid.program:duplicate.resource)
#@ config: allocation

from . import interface_a1
from .subdir import interface_a2
import tests.resources.language.inter_contract.resource.interface_a2 as a3
from . import interface_b

@public
def foo():
    pass
