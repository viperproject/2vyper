#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract C:
    def f() -> int128: modifying


c: C


#:: ExpectedOutput(invalid.program:spec.call)
#@ invariant: self.c.f() == 0


@public
def __init__():
    pass
