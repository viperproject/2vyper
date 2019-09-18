#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract Foo:
    def bar(): modifying


#@ preserves:
    #:: ExpectedOutput(postcondition.not.wellformed:constant.balance)
    #@ always ensures: self.balance == old(self.balance)


@public
def test():
    old_balance: wei_value = self.balance
    Foo(msg.sender).bar()
    assert self.balance == old_balance, UNREACHABLE
