#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ invariant: lemma.bar()

#@ lemma_def bar():
    #@ True

#@ invariant: lemma.bar()

#@ requires: lemma.bar()
@private
def foo1():
    pass

#@ ensures: lemma.bar()
@public
def foo2():
    pass

#@ check: lemma.bar()
@private
def foo3():
    pass

#@ check: lemma.bar()
@public
def foo4():
    pass
