#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


Event1: event({a: int128, b: uint256})
Event2: event({a: int128})
Event3: event({a: int128[2], b: bool})


#@ check: event(Event1(1, 2)) ==> forall({a: int128}, not event(Event2(a)))
#@ check: event(Event1(1, 2)) ==> forall({a: int128[2], b: bool}, not event(Event3(a, b)))
#@ check: event(Event2(0)) ==> forall({a: int128, b: uint256}, not event(Event1(a, b)))
#@ check: event(Event2(0)) ==> forall({a: int128[2], b: bool}, not event(Event3(a, b)))
#@ check: event(Event3([1, 2], True)) ==> forall({a: int128, b: uint256}, not event(Event1(a, b)))
#@ check: event(Event3([1, 2], True)) ==> forall({a: int128}, not event(Event2(a)))
@public
def emit_event(bb: bytes32, bt: bytes32, data: bytes[256]):
    raw_log([bb, bt], data)


#:: ExpectedOutput(check.violated:assertion.false)
#@ check: forall({a: int128, b: uint256}, not event(Event1(a, b)))
@public
def emit_event_fail1(bb: bytes32, bt: bytes32, data: bytes[256]):
    raw_log([bb, bt], data)


#:: ExpectedOutput(check.violated:assertion.false)
#@ check: forall({a: int128}, not event(Event2(a)))
@public
def emit_event_fail2(bb: bytes32, bt: bytes32, data: bytes[256]):
    raw_log([bb, bt], data)


#:: ExpectedOutput(check.violated:assertion.false)
#@ check: forall({a: int128[2], b: bool}, not event(Event3(a, b)))
@public
def emit_event_fail3(bb: bytes32, bt: bytes32, data: bytes[256]):
    raw_log([bb, bt], data)
