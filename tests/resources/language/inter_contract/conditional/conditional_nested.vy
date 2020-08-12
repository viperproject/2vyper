#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#:: ExpectedOutput(invalid.program:invalid.caller.private)
#@ caller private: conditional(conditional(caller() == caller(), True), True)

@public
def foo() -> address:
    raise "Not implemented"
