#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Verification took   3.22 seconds. [benchmark=10] (With loop invariants)
# Verification took  11.86 seconds. [benchmark=10] (With loop unrolling)

SomeEvent: event({value: int128})

#@ check: success() ==> event(SomeEvent(1))
#@ check: success() ==> event(SomeEvent(42), 42)
#@ check: success() ==> forall({i: int128}, {event(SomeEvent(i))}, (i >= 100 and i < 200) ==> event(SomeEvent(i)))
@public
def foo(a: int128):
    log.SomeEvent(1)
    for i in range(42):
        # Preserve event through loop
        #@ invariant: event(SomeEvent(1))
        # Generate events in loop
        #@ invariant: event(SomeEvent(42), loop_iteration(i))
        # All other events are zero
        #@ invariant: forall({i: int128}, {event(SomeEvent(i))}, (i != 1 and i != 42) ==> event(SomeEvent(i), 0))
        log.SomeEvent(42)

    for i in range(100, 200):
        # Preserve events through loop
        #@ invariant: event(SomeEvent(1))
        #@ invariant: event(SomeEvent(42), 42)
        # Generate events in loop
        #@ invariant: forall({j: int128}, {event(SomeEvent(j))}, (j >= 100 and j < i) ==> event(SomeEvent(j)))
        # Events not generated yet are zero
        #@ invariant: forall({j: int128}, {event(SomeEvent(j))}, (j >= i and j < 200) ==> event(SomeEvent(j), 0))
        log.SomeEvent(i)
