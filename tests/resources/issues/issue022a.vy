#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#:: ExpectedOutput(invalid.program:invalid.ghost.code)
#@ temp: bool

#@ ensures: success(if_not=out_of_gas) if self.temp else True
@public
def foo():
    pass