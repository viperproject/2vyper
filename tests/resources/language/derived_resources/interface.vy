#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, no_derived_wei_resource

#@ interface

#@ resource: r()
#@ resource: a(f: uint256)

@public
def foo():
    raise "Not implemented"

#@ performs: offer[r <-> r](1, 0, to=self, times=1)
@public
def offer_r():
    raise "Not implemented"

#@ performs: trust(self, True)
@public
def trust():
    raise "Not implemented"

#@ performs: create[r](1)
@public
def create_r():
    raise "Not implemented"