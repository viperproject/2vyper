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
#@ ensures: event(SomeEvent(42), 1) if a else True
#@ check: False
@private
def if_test1(a: bool):
    if a:
        log.SomeEvent(42)

#@ requires: event(SomeEvent(1), 0)
#@ requires: event(SomeEvent(42), 0)
#@ ensures: event(SomeEvent(42), 1) if a else event(SomeEvent(1), 1)
#@ check: False
@private
def if_test2(a: bool):
    if a:
        log.SomeEvent(42)
    else:
        log.SomeEvent(1)

#@ check: success() ==> event(SomeEvent(42), 1)
@public
def bar():
    self.if_test1(True)

#:: ExpectedOutput(check.violated:assertion.false)
#@ check: success() ==> event(SomeEvent(42), 1)
@public
def bar_fail():
    self.if_test1(False)


#@ check: success() ==> (event(SomeEvent(42), 1) if arg else event(SomeEvent(1), 1))
#@ check: (success() and arg) ==> event(SomeEvent(42), 1)
#@ check: (success() and not arg) ==> event(SomeEvent(1), 1)
@public
def baz():
    arg: bool = True
    self.if_test2(arg)
    C(msg.sender).send()
    arg = False
    self.if_test2(arg)



