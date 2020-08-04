#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract C:
    def f() -> bool: constant

#@ lemma_def bar():
    #:: ExpectedOutput(invalid.program:invalid.lemma)
    #@ C(0x000000001000000000010000000000000600000a).f()

@public
def foo():
    pass
