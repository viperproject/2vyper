#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#:: ExpectedOutput(invalid.program:invalid.type)
#@ ensures: success() ==> result() == old(a + b)
@public
def add_arrays(a: int128[19], b: int128[19]) -> int128[19]:
    return a