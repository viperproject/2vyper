#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

@public
def foo(a: int128):
    for i in [1, 1, 2, 3, 5, 8]:
        #@ invariant: i == loop_array(i)[loop_iteration(i)]
        #@ invariant: forall({j: int128}, j in previous(i) ==> j in loop_array(i))
        #@ invariant: loop_iteration(i) == 5 ==> sum(loop_array(i)) == sum(previous(i)) + i
        #@ invariant: loop_array(i)[loop_iteration(i)] == [1, 1, 2, 3, 5, 8][loop_iteration(i)]
        #@ invariant: forall({j: uint256}, j < loop_iteration(i) ==> previous(i)[j] == loop_array(i)[j])
        #@ invariant: loop_iteration(i) > 0 ==> previous(i)[loop_iteration(i) - 1] == loop_array(i)[loop_iteration(i) - 1]
        pass
