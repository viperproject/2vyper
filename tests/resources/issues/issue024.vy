#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

l1: constant(bool) = 1 > 0
l2: constant(bool) = 1 >= 0
l3: constant(bool) = 1 <= 0
l4: constant(bool) = 1 < 0
l5: constant(bool) = 1 != 0
l6: constant(bool) = 1 == 0

#@ ensures: l1
#@ ensures: l2
#@ ensures: not l3
#@ ensures: not l4
#@ ensures: l5
#@ ensures: not l6
@public
def foo():
    pass
