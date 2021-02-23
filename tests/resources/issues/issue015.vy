#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

#@ resource: good()

#@ invariant: sum(allocated()) == 0 and sum(allocated[good]()) == 0

@public
def foo():
    a: address = 0x000000001000000000010000000000000600000a
    #@ offer(0, 1, to=msg.sender, times=1, actor=a)
    #@ offer(1, 1, to=msg.sender, times=0, actor=a)
    #@ revoke(0, 1, to=msg.sender, actor=a)
    #@ reallocate(0, to=msg.sender, actor=a)
    #@ create[good](0, to=msg.sender, actor=a)
    #@ destroy[good](0, actor=a)
