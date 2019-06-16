#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

owner: address

@public
def set_owner(a: address) -> address:
    b: address = a
    b = a
    return b

@public
def compare_addresses(a: address, b: address) -> address:
    if a == b:
        return a
    else:
        return b

@public
def lit():
    a: address = 0x0000000000000000000000000000000000000000
    b: address = 0x000000001000000000010000000000000600000a