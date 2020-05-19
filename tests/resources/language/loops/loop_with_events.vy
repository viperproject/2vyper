#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Verification took   2.27 seconds. [benchmark=10] (With loop invariants)
# Verification took   2.10 seconds. [benchmark=10] (With loop unrolling)

SomeEvent: event({value: int128})

#@ check: success() ==> event(SomeEvent(1))
#@ check: success() ==> event(SomeEvent(42), 42)
@public
def foo(a: int128):
    log.SomeEvent(1)
    for i in range(42):
        # Preserve event through loop
        #@ invariant: event(SomeEvent(1))
        # Generate events in loop
        #@ invariant: event(SomeEvent(42), loop_iteration(i))
        log.SomeEvent(42)
