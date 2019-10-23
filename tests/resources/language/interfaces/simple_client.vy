#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import simple


#@ ensures: implies(arg <= 0, not success())
#@ ensures: implies(success(), result() == arg + 1)
@public
def use_simple(at: address, arg: int128) -> int128:
    return simple(at).positive(arg) + 1


#@ ensures: implies(arg <= 0, not success())
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() > arg)
@public
def use_simple_fail(at: address, arg: int128) -> int128:
    return simple(at).positive(arg)


@public
def use_simple_not_welldefined_fail(at: address, arg: int128) -> int128:
    #:: ExpectedOutput(interface.postcondition.not.wellformed:division.by.zero)
    return simple(at).positive_not_welldefined(arg)
