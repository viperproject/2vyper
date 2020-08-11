#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ lemma_def lemma():
    #@ True

#@ requires: lemma == 0
#@ lemma_def bar(lemma: int128):
    #@ lemma == 0
    #@ lemma.lemma()

#@pure
@private
@constant
def lemma() -> bool:
    return True

@public
def foo():
    lemma: int128 = 0
    #@ lemma_assert lemma.bar(lemma) and lemma.lemma() and result(self.lemma())
