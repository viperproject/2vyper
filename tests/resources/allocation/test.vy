#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource, trust_casts

from . import IERC20_alloc

token: IERC20_alloc

#@ preserves:
    #@ always ensures: trust_no_one(self, self.token)
    #@ always ensures: no_offers[token[self.token]](self)
    #@ always ensures: allocated[token[self.token]](self) >= old(allocated[token[self.token]](self))

#@ invariant: self.token == old(self.token)
#@ inter contract invariant: allocated[token[self.token]](self) >= old(allocated[token[self.token]](self))
#@ inter contract invariant: trust_no_one(self, self.token)
#@ inter contract invariant: no_offers[token[self.token]](self)


# ensures: success() ==> allocated[token[self.token]](self) >= old(allocated[token[self.token]](self)) + v
@public
def test(a: address, v: uint256):
    self.token.transferFrom(a, self, v)