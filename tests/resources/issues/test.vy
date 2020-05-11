#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ ensures: res == 255
@public
def foo():
    res: int128 = 0
    for i in range(234908):
        #@ invariant: res == i
        #@ invariant: i <= 255
        if i == 255:
            break
        res += 1
        if i > 255:
            continue

        # Base case:
        #    // known property about loop variable
        #    assume idx == 0
        #    i = array[idx]
        #    // check loop invariants before iteration 0
        #    assert that res == i
        #    assert i <= 255
        # Step case:
        #    havoc state (present and old) && used variables in loop && heap stuff (just events)
        #       -> same as for caller of a non-constant private function PLUS used names in loop
        #       -> the analyzer should provide the "used names in loop" information
        #    // known property about loop variable
        #    assume 0 <= idx && idx < |array|
        #    i = array[idx]
        #    // assume loop invariants
        #    assume res == i
        #    assume i <= 255
        #    // loop body
        #    if i == 255:
        #        goto after_loop
        #    res += 1
        #    if i > 255:
        #        goto next_iteration
        #    // end of loop body
        #    label next_iteration
        #    idx += 1
        #    if idx == |array|:
        #        goto after_loop
        #    i = array[idx + 1]
        #    // check loop invariants for iteration idx + 1
        #    assert res == i + 1
        #    assert i + 1 <= 255
        #    assume False  // <- Kill this branch
        #    // after loop
        #    label after_loop

