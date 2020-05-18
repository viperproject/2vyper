#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract C:
    def send(): modifying

SomeEvent: event({_value: uint256})

#@ requires: event(SomeEvent(42), 0)
#@ ensures: a ==> event(SomeEvent(42), 1)
#@ ensures: b ==> event(SomeEvent(42), 1)
#@ check: False
@private
def disjunction_test(a: bool, b: bool):
    if a or b:
        log.SomeEvent(42)

#@ requires: forall({i: uint256}, {event(SomeEvent(i))}, i >= 3 and i < 10 ==> event(SomeEvent(i), 1))
#@ ensures: success() ==> forall({i: uint256}, {event(SomeEvent(i))}, i >= 3 and i < 10 ==> event(SomeEvent(i), 1))
#@ ensures: success() ==> forall({i: uint256}, {event(SomeEvent(i))}, i >= 3 and i < 10 ==> event(SomeEvent(i), 1))
#@ check: forall({i: uint256}, {event(SomeEvent(i))}, i >= 3 and i < 10 ==> event(SomeEvent(i), 1))
@private
def forall_event_test(a: address):
    C(a).send()
    log.SomeEvent(3)
    log.SomeEvent(4)
    log.SomeEvent(5)
    log.SomeEvent(6)
    log.SomeEvent(7)
    log.SomeEvent(8)
    log.SomeEvent(9)

#@ check: success() ==> forall({i: uint256}, i >= 3 and i < 10 ==> event(SomeEvent(i), 1))
@public
def foo():
    log.SomeEvent(3)
    log.SomeEvent(4)
    log.SomeEvent(5)
    log.SomeEvent(6)
    log.SomeEvent(7)
    log.SomeEvent(8)
    log.SomeEvent(9)
    self.forall_event_test(msg.sender)

#@ check: success() ==> event(SomeEvent(42), 1)
@public
def bar():
    self.disjunction_test(True, False)
    C(msg.sender).send()
    self.disjunction_test(False, True)
    C(msg.sender).send()
    self.disjunction_test(True, True)

#:: ExpectedOutput(check.violated:assertion.false)
#@ check: success() ==> event(SomeEvent(42), 1)
@public
def bar_fail():
    self.disjunction_test(False, False)


