#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

pendingReturns: public(map(address, wei_value))

#:: ExpectedOutput(invalid.program:duplicate.resource)
#@ resource: wei(id: address)

#@ invariant: forall({a: address}, allocated[wei(self)](a) == self.pendingReturns[a])

@private
def foo():
    pass
