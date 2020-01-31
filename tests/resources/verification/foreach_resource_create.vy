#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation


owner: address


#@ resource: token(owner: address)


#@ invariant: forall({a: address}, {allocated[wei](a)}, allocated[wei](a) == 0)
#:: Label(ALLOC_OWNER)
#@ invariant: forall({o: address}, {allocated[token(o)](self.owner)}, allocated[token(o)](self.owner) == (2 if o == self.owner else 1))
#:: Label(ALLOC_ALL)
#@ invariant: forall({o: address, a: address}, {allocated[token(o)](a)}, a != self.owner ==> allocated[token(o)](a) == (1 if o == a else 0))
#@ invariant: forall({o: address}, {allocated[creator(token(o))](o)}, allocated[creator(token(o))](o) == 1)


@public
def __init__():
    self.owner = msg.sender

    #@ foreach({a: address}, create[token(a)](1, to=a))
    #@ foreach({a: address}, create[token(a)](1))
    #@ foreach({a: address}, create[creator(token(a))](1, to=a))


#:: ExpectedOutput(invariant.violated:assertion.false, ALLOC_OWNER) | ExpectedOutput(carbon)(invariant.violated:assertion.false, ALLOC_ALL)
@public
def foreach_create_inv_fail():
    #@ foreach({a: address}, create[token(msg.sender)](1, to=a))
    pass


#:: ExpectedOutput(carbon)(invariant.violated:assertion.false, ALLOC_OWNER) | ExpectedOutput(carbon)(invariant.violated:assertion.false, ALLOC_ALL)
@public
def foreach_create_create_fail():
    #:: ExpectedOutput(create.failed:not.a.creator)
    #@ foreach({a: address}, create[token(a)](1, to=a))
    pass
