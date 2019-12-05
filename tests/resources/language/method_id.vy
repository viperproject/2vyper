#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
def get_method_id_32() -> bytes32:
    return method_id('somefunc(int128)', bytes32)


@public
def get_method_id_4() -> bytes[4]:
    return method_id('funcsome(int128)', bytes[4])


#@ ensures: len(method_id('somefunc(int128)', bytes[4])) == 4
@public
def check():
    pass


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: method_id('blabla', bytes32) == method_id('balabala', bytes32)
@public
def check_fail():
    pass
