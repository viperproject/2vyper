#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ invariant: sum(sent()) == old(sum(sent()))


@public
def call_sender():
    #:: ExpectedOutput(call.invariant:assertion.false)
    send(msg.sender, self.balance)
