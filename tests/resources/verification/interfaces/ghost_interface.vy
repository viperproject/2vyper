#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ interface


#@ ghost:
    #@ def _some_val() -> int128: ...
    #@ def _some_uval() -> uint256: ...


@public
def some_func():
    pass
