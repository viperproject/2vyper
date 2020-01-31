#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


owner: address
counter: int128


#@ resource: token()


#@ invariant: sum(allocated[wei]()) == 0
#:: Label(INV)
#@ invariant: forall({a: address}, {allocated[token](a)}, allocated[token](a) == (self.counter if a == self.owner else 0))
#@ invariant: allocated[creator(token)](self.owner) == 1


@public
def __init__():
    self.owner = msg.sender
    #@ create[creator(token)](1)


@public
def foo():
    if msg.sender == self.owner:
        self.counter += 1

    #@ create[token](1 if msg.sender == self.owner else 0)


#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, INV)
@public
def foo_fail():
    if msg.sender == self.owner:
        self.counter += 1

    #:: ExpectedOutput(create.failed:not.a.creator)
    #@ create[token](1)
