#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import interface

implements: interface


@public
def foo(i: int128) -> int128:
    assert i > 0
    return i


#:: ExpectedOutput(postcondition.not.implemented:assertion.false)
@public
def bar(u: uint256) -> uint256:
    return u + 1
