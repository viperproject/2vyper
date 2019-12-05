#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


owner: address


@public
@payable
def __init__():
    pass


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


@public
def get_codesize(a: address) -> int128:
    return a.codesize


@public
def get_is_contract(a: address) -> bool:
    return a.is_contract


@public
def get_balance(a: address) -> wei_value:
    return a.balance


@public
def get_0x1_balance() -> wei_value:
    a: wei_value = 0x0000000000000000000000000000000000000001.balance
    assert a == 0x0000000000000000000000000000000000000001.balance, UNREACHABLE
    send(0x0000000000000000000000000000000000000001, self.balance)
    #:: ExpectedOutput(assert.failed:assertion.false)
    assert a == 0x0000000000000000000000000000000000000001.balance, UNREACHABLE
    return a


@public
def get_self_codesize() -> int128:
    return self.codesize


@public
def get_self_is_contract() -> bool:
    return self.is_contract


@public
def get_self_balance() -> wei_value:
    return self.balance
