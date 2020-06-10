#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract C:
    def send(): modifying


#@ ensures: not out_of_gas() ==> success()
#@ check: not out_of_gas() ==> success()
@public
def foo():
    pass

#@ ensures: not failed(a) ==> success(if_not=out_of_gas)
#@ check: success() ==> not failed(a)
@public
def bar(a: address):
    C(a).send()

#@ ensures: not overflow() ==> success(if_not=out_of_gas)
#@ check: not overflow() ==> success(if_not=out_of_gas)
@public
def baz(i: int128) -> int128:
    return i + 1
