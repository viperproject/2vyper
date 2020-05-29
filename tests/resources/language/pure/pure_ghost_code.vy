#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@pure
@constant
@private
def foo() -> int128:
    #:: ExpectedOutput(invalid.program:invalid.pure)
    #@ MAX_INT128 + 1
    return 0

#@ ensures: success(self.foo())
@public
def bar():
    pass