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


#:: ExpectedOutput(invariant.violated:assertion.false)
#@ invariant: self.b == old(self.b)


@public
@payable
def __init__():
    self.a = 12
    self.b = 24
    Client(msg.sender).pay(value=self.balance)
    self.b = 16
