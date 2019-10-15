#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

perm: int128

#@ invariant: forall({axiom: int128, mp: map(int128, uint256)}, {mp[axiom]}, mp[axiom] == mp[axiom])

@public
def assume():
    pass

@public
def acc():
    domain: int128 = 0
