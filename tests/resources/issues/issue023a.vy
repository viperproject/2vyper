#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

l: constant(int128) = 5

#@ ensures: sum(range((1 + 5 + l - 1) / 5)) == 1
#@ ensures: sum(range(a, a + (((1 + 5 + l - 1) / 5) - 1))) == a
#@ ensures: sum(range(7 + l, 11 + (1 + 5 + l - 1) / 5)) == 12
@public
def foo(a: int128):
    for i in range((1 + 5 + l - 1) / 5):
        pass

    for i in range(a, a + (((1 + 5 + l - 1) / 5) - 1)):
        pass

    for i in range(7 + l, 11 + (1 + 5 + l - 1) / 5):
        pass
