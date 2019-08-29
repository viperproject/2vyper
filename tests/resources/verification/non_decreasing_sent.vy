#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
@payable
def __default__():
    pass


#@ ensures: sent(msg.sender) >= old(sent(msg.sender))
#@ ensures: implies(success(), sent(msg.sender) >= old(sent(msg.sender)) + as_wei_value(1, "wei"))
@public
def pay():
    send(msg.sender, as_wei_value(1, "wei"))


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: sent(msg.sender) > old(sent(msg.sender))
@public
def pay_fail():
    send(msg.sender, as_wei_value(1, "wei"))
