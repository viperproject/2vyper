#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: no_gas


owner: address


#@ ensures: not selfdestruct()
@public
def __init__():
    self.owner = msg.sender


#@ ensures: implies(msg.sender == self.owner, selfdestruct() and self.balance == 0 and 
#@     sent(self.owner) == old(sent(self.owner) + old(self.balance)))
@public
def destroy():
    assert msg.sender == self.owner
    selfdestruct(msg.sender)


#@ ensures: implies(msg.sender == self.owner, selfdestruct() and self.balance == 0)
@public
def destroy_to_self():
    assert msg.sender == self.owner
    selfdestruct(self)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: not selfdestruct()
@public
def no_destroy_fail():
    return