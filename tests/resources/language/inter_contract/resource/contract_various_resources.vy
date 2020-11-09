#:: IgnoreFile(0)

#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: allocation

from . import interface_a1
from . import interface_a2
from . import interface_b
from . import interface_d

implements: interface_d

g: interface_d
i: interface_b
j: interface_a1
k: interface_a2

#@ resource: a()

# WEI
#@ invariant: forall({a: address}, allocated(a) == 0)
#@ invariant: forall({a: address}, allocated[wei](a) == 0)
#@ invariant: forall({a: address}, allocated[wei()](a) == 0)
#@ invariant: forall({a: address}, allocated[wei[self]](a) == 0)
#@ invariant: forall({a: address}, allocated[wei[self]()](a) == 0)
#@ invariant: forall({a: address}, allocated[wei[self.g]()](a) == 0)
#@ invariant: forall({a: address}, allocated[wei[self.i]](a) == 0)


# Normal resources
#@ invariant: forall({a: address}, allocated[a](a) == 0)
#@ invariant: forall({a: address}, allocated[a()](a) == 0)
#@ invariant: forall({a: address}, allocated[a[self]](a) == 0)
#@ invariant: forall({a: address}, allocated[a[self]()](a) == 0)
#@ invariant: forall({a: address}, allocated[interface_a1.a[self.j]](a) == 0)
#@ invariant: forall({a: address}, allocated[b[self.i]](a) == 0)
#@ invariant: forall({a: address}, allocated[b[self.i]()](a) == 0)
#@ invariant: forall({a: address}, allocated[interface_b.b[self.i]](a) == 0)
#@ invariant: forall({a: address}, allocated[interface_b.b[self.i]()](a) == 0)

# Interface resources
#@ invariant: forall({a: address}, allocated[d](a) == 0)
#@ invariant: forall({a: address}, allocated[d()](a) == 0)
#@ invariant: forall({a: address}, allocated[d[self]](a) == 0)
#@ invariant: forall({a: address}, allocated[d[self]()](a) == 0)
#@ invariant: forall({a: address}, allocated[interface_d.d](a) == 0)
#@ invariant: forall({a: address}, allocated[interface_d.d()](a) == 0)
#@ invariant: forall({a: address}, allocated[interface_d.d[self]](a) == 0)
#@ invariant: forall({a: address}, allocated[interface_d.d[self]()](a) == 0)
#@ invariant: forall({a: address}, allocated[interface_d.d[self.g]](a) == 0)
#@ invariant: forall({a: address}, allocated[interface_d.d[self.g]()](a) == 0)


#@ performs: reallocate[d](0, to=msg.sender)
#@ performs: reallocate[d()](0, to=msg.sender)
#@ performs: reallocate[interface_d.d](0, to=msg.sender)
#@ performs: reallocate[interface_d.d()](0, to=msg.sender)
#@ performs: reallocate[interface_d.d()](0, to=msg.sender)
@public
def foo():
    send(msg.sender, 0)
    #@ reallocate[d](0, to=msg.sender)
    #@ reallocate[d()](0, to=msg.sender)
    #@ reallocate[interface_d.d](0, to=msg.sender)
    #@ reallocate[interface_d.d()](0, to=msg.sender)
    #@ reallocate[interface_d.d()](0, to=msg.sender)
