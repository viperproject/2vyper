#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

#:: ExpectedOutput(invalid.program:invalid.local.var)
#@ performs: reallocate(temp, to=msg.sender)
@private
def foo():
    temp: int128 = 0
    #@ reallocate(temp, to=msg.sender)
