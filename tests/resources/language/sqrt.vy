#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: implies(d < 0.0, not success())
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success(if_not=out_of_gas)
@public
def get_sqrt(d: decimal) -> decimal:
    return sqrt(d)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), implies(d == 2.0, result() == 1.0))
@public
def get_sqrt_wrong_result(d: decimal) -> decimal:
    return sqrt(d)
