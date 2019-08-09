#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


owner: address


#@ invariant: forall({a: address}, {sent(a)}, sent(a) >= old(sent(a)))
#:: Label(WD)
#@ invariant: accessible(self.owner, self.balance)


@public
def __init__():
    self.owner = msg.sender


@public
@payable
def __default__():
    pass


#:: ExpectedOutput(invariant.violated:assertion.false, WD)
@public
def withdraw():
    assert msg.sender != self.owner
    send(msg.sender, self.balance)
