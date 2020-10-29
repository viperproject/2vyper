#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#:: ExpectedOutput(invalid.program:precondition.call)
#@ requires: offer(1, 1, to=ZERO_ADDRESS, times=1) == offer(1, 1, to=ZERO_ADDRESS, times=1)
@private
def foo():
    pass

@public
def bar():
    pass
