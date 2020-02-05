#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation, no_performs


owner: address


#@ resource: token(owner: address)
#@ resource: free(owner: address)


#@ invariant: forall({a: address}, {allocated[wei](a)}, allocated[wei](a) == 0)

#:: Label(ALLOC_OWNER)
#@ invariant: forall({o: address}, {allocated[token(o)](self.owner)}, allocated[token(o)](self.owner) == (2 if o == self.owner else 1))
#:: Label(ALLOC_ALL)
#@ invariant: forall({o: address, a: address}, {allocated[token(o)](a)}, a != self.owner ==> allocated[token(o)](a) == (1 if o == a else 0))
#@ invariant: forall({o: address}, {allocated[creator(token(o))](o)}, allocated[creator(token(o))](o) == 1)

#@ invariant: forall({o: address, a: address}, {allocated[free(o)](a)}, allocated[free(o)](a) == 0)
#@ invariant: forall({o: address, a: address}, {allocated[creator(free(o))](a)}, allocated[creator(free(o))](a) == 1)


@public
def __init__():
    self.owner = msg.sender

    #@ foreach({a: address}, create[token(a)](1, to=a))
    #@ foreach({a: address}, create[token(a)](1))
    #@ foreach({a: address}, create[creator(token(a))](1, to=a))
    #@ foreach({o: address, a: address}, create[creator(free(o))](1, to=a))


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


@public
def foreach_offer():
    #@ foreach({o: address}, offer[wei <-> token(o)](1, 1, to=o, times=1))
    #@ foreach({o: address}, revoke[wei <-> token(o)](1, 1, to=o))
    pass


@public
def do_nothing():
    #@ foreach({o: address}, create[free(o)](1))
    #@ foreach({o: address}, destroy[free(o)](1))
    pass


@public
def do_nothing_fail():
    #:: ExpectedOutput(destroy.failed:insufficient.funds)
    #@ foreach({o: address}, destroy[free(o)](1))
    pass
