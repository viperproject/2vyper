#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

@public
def foo():
    #:: ExpectedOutput(invalid.program:ether.change)
    #@ create[wei](1)
    pass
