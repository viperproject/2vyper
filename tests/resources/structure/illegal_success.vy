#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#:: ExpectedOutput(invalid.program:spec.success)
#@ ensures: success(if_not=out_of_gas or sender_failed or ILLEGAL_CONDITION)
@public
def fail():
    pass