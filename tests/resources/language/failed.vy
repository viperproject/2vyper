#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract C:
    def c() -> int128: constant
    def f(): modifying


#@ ensures: not out_of_gas() and not failed(msg.sender) ==> success()
@public
def call_c() -> int128:
    return C(msg.sender).c()


#@ ensures: not out_of_gas() and not failed(msg.sender) ==> success()
@public
def call_f():
    C(msg.sender).f(value=self.balance)


#@ ensures: not out_of_gas() and not failed(msg.sender) ==> success()
@public
def send_msg_sender():
    send(msg.sender, self.balance)


#@ ensures: not out_of_gas() and not failed(a) ==> success()
@public
def call_addr(a: address) -> int128:
    return C(a).c()


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: not out_of_gas() and not failed(msg.sender) ==> success()
@public
def call_addr_fail(a: address) -> int128:
    return C(a).c()
