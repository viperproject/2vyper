#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation, trust_casts

from . import interface_a1
from . import interface_a2
from . import interface_b

i: interface_b
j: interface_a1
k: interface_a2

#@ resource: a()

#@ invariant: forall({a: address}, allocated(a) == 0)
#@ invariant: forall({a: address}, allocated[a](a) == 0)
#@ inter contract invariant: forall({a: address}, allocated[interface_b.b[self.i]](a) == 0)
#@ inter contract invariant: forall({a: address}, allocated[interface_a1.a[self.j]](a) == 0)
#@ inter contract invariant: forall({a: address}, allocated[interface_a2.a[self.k]](a) == 0)

@public
def __init__():
    pass

@public
def foo():
    send(msg.sender, 0)
