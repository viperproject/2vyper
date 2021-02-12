#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

creator: address

#@ resource: good()

#@ invariant: forall({a: address}, {allocated[wei](a)}, allocated[wei](a) == 0)
#@ invariant: forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.creator else 0))

@public
def __init__():
    self.creator = msg.sender
    #@ create[good](1, to=msg.sender)
    #@ foreach({a: address, v: wei_value}, {offer[good <-> wei](1, v, to=a, times=1)}, offer[good <-> wei](1, v, to=a, times=1))
