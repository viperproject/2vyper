#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ always ensures: implies(success(), success(if_not=sender_failed))


#@ ensures: success(if_not=sender_failed)
@public
def success_msg_sender():
    send(msg.sender, self.balance)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success(if_not=sender_failed)
@public
def success_msg_sender_fail():
    assert False


#@ ensures: implies(self.balance >= as_wei_value(5, "ether"), success(if_not=sender_failed))
@public
def cond_success_msg_sender():
    send(msg.sender, as_wei_value(5, "ether"))


@public
def succ_is_succmsg(a: int128):
    assert a > 0
    send(msg.sender, self.balance)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(if_not=sender_failed), success())
@public
def succmsg_is_succ_fail(a: int128):
    send(msg.sender, self.balance)
