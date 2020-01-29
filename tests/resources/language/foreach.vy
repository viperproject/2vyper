#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


owner: address
sold: bool
aborted: bool


#@ resource: good()
#@ resource: nothing()


#@ invariant: self.owner == old(self.owner)
#@ invariant: old(self.aborted) ==> self.aborted
#@ invariant: old(self.sold) ==> self.sold

#@ invariant: sum(allocated[wei]()) == 0 and sum(allocated[nothing]()) == 0
#@ invariant: forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.owner and not self.sold else 0))

#@ invariant: not self.sold and not self.aborted ==> forall({a: address}, offered[good <-> nothing](1, 0, self.owner, a) == 1)
#@ invariant: self.aborted ==> forall({a: address}, offered[good <-> nothing](1, 0, self.owner, a) == 0)


#@ ensures: success() ==> offered[good <-> nothing](1, 0, self.owner, 0x1) == 1
@public
def __init__(t: address):
    self.owner = msg.sender
    #@ create[good](1)
    #@ foreach({a: address}, offer[good <-> nothing](1, 0, to=a, times=1))


@private
@constant
def over() -> bool:
    return self.sold or self.aborted


@public
def abort():
    assert msg.sender == self.owner
    assert not self.over()

    #@ foreach({a: address}, revoke[good <-> nothing](1, 0, to=a))

    self.aborted = True


@public
def get():
    assert not self.over()

    #@ exchange[good <-> nothing](1, 0, self.owner, msg.sender, times=1)
    #@ destroy[good](1)

    self.sold = True
