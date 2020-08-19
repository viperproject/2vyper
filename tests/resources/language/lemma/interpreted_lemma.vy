#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interpreted
#@ lemma_def foo():
    #@ 20 * 20 == 400

#@ ensures: lemma.foo()
#@ ensures: x == 20 ==> x * x * 124901284 == 49960513600
@public
def test(x: int128):
    pass
