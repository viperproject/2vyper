#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract lemma:
    def lemma() -> bool: constant

lemma: lemma

#@ lemma_def lemma():
    #@ True

#@ requires: lemma == 0
#@ lemma_def bar(lemma: int128):
    #@ lemma == 0
    #@ lemma.lemma()

@public
def foo():
    assert_modifiable(self.lemma.lemma())
    #@ lemma_assert lemma.bar(0) and lemma.lemma()
