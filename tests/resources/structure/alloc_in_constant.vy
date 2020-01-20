#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


@public
@constant
def get_zero() -> int128:
    #:: ExpectedOutput(invalid.program:alloc.in.constant)
    #@ reallocate(1, to=msg.sender, times=1)
    return 0
