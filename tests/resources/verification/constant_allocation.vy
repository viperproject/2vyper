#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


owner: address
flag: bool


#@ invariant: self.owner == old(self.owner)
#@ invariant: allocated() == old(allocated())


#:: ExpectedOutput(leakcheck.failed:allocation.leaked)
@public
@payable
def __init__():
    self.owner = msg.sender


#:: ExpectedOutput(leakcheck.failed:allocation.leaked)
@public
def do_nothing():
    pass
