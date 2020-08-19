#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interpreted
#@ lemma_def foo(x: int128):
    #:: ExpectedOutput(lemma.step.invalid:assertion.false)
    #@ 20 * 20 == 401
    #@ x == 20 ==> x * 20 == x * x

#@ lemma_def bar(x: int128):
    #:: ExpectedOutput(lemma.step.invalid:assertion.false)
    #@ 20 * 20 == 401
    #@ x == 20 ==> x * 20 == x * x


#@ ensures: lemma.foo(x)
@public
def foo(x: int128):
    pass


#@ ensures: lemma.bar(x)
@public
def bar(x: int128):
    pass
