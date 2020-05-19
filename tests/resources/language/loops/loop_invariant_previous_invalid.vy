#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

@public
def foo(a: int128):
    for i in range(2):
        #:: ExpectedOutput(loop.invariant.not.wellformed:seq.index.length)
        #@ invariant: previous(i)[loop_iteration(i)] == 0
        pass
