#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@pure
@constant
@private
def check_arg(i: int128):
    assert i > 0

#:: ExpectedOutput(invalid.program:spec.result)
#@ ensures: success(self.check_arg(i)) ==> result(self.check_arg(i)) == result(self.check_arg(i))
@public
def foo():
    pass