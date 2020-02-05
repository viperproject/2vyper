#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation, no_performs


owner: address
sold: bool
aborted: bool


#@ resource: nothing()
#@ resource: good()


#@ invariant: self.owner == old(self.owner)
#@ invariant: old(self.aborted) ==> self.aborted
#@ invariant: old(self.sold) ==> self.sold

#@ invariant: forall({a: address}, {allocated[wei](a)}, allocated[wei](a) == 0)
#@ invariant: forall({a: address}, {allocated[nothing](a)}, allocated[nothing](a) == 0)
#@ invariant: forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.owner and not self.sold else 0))

#@ invariant: forall({a: address}, {allocated[creator(good)](a)}, allocated[creator(good)](a) == 1)

#@ invariant: not self.sold and not self.aborted ==> forall({a: address}, offered[good <-> nothing](1, 0, self.owner, a) == 1)
#@ invariant: self.aborted ==> forall({a: address}, offered[good <-> nothing](1, 0, self.owner, a) == 0)


#@ ensures: success() ==> offered[good <-> nothing](1, 0, self.owner, 0x1) == 1
@public
def __init__(t: address):
    self.owner = msg.sender
    #@ create[good](1)
    #@ foreach({a: address}, create[creator(good)](1, to=a))
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


@public
def do_nothing():
    #@ create[good](1)
    pass
    #@ destroy[good](1)
