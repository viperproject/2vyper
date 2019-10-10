#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract Client:
    def pay(): modifying


a: int128
b: uint256


#@ invariant: self.a >= old(self.a)
#@ invariant: self.b == old(self.b)

#@ always check: implies(success(), self.a == old(self.a) or self.a == old(self.a) + 12)


@public
@payable
def __init__():
    self.a = 12
    self.b = 24
    Client(msg.sender).pay(value=self.balance / 2)
    self.a += 12
    Client(msg.sender).pay(value=self.balance / 2)
    self.a += 12
    send(msg.sender, self.balance / 2)
    self.a += 12

