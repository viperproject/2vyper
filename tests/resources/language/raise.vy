#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ ensures: not success()
@public
def test_raise():
    raise "Error"


#@ ensures: implies(a, not success())
@public
def test_raise_conditional(a: bool):
    if a:
        raise "Error"
