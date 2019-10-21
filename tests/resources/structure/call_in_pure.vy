#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract C:
    def f() -> bool: constant


#@ pure
@public
@constant
def get_b(a: address) -> bool:
     #:: ExpectedOutput(invalid.program:pure.not.pure)
    return C(a).f()
