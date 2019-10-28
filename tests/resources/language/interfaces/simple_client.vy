#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import simple


@public
@payable
def __default__():
    pass


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


@public
def use_simple_msg_sender(at: address):
    a: address = simple(at).use_msg_sender()
    assert a == self, UNREACHABLE


@public
def use_simple_msg_value(at: address):
    amount: wei_value = simple(at).use_msg_value(value=as_wei_value(1, "ether"))
    assert amount == as_wei_value(1, "ether"), UNREACHABLE


#@ ensures: not success()
@public
def use_simple_msg_sender_with_ether(at: address):
    simple(at).use_msg_sender(value=as_wei_value(1, "ether"))


#@ ensures: not success()
@public
def use_simple_msg_value_without_ether(at: address):
    simple(at).use_msg_value(value=ZERO_WEI)


@public
def use_simple_pure(at: address, i: int128):
    first: int128 = simple(at).pure(i)
    second: int128 = simple(at).pure(i)
    assert first == second, UNREACHABLE

    simple(at).use_msg_value(value=as_wei_value(1, "ether"))

    third: int128 = simple(at).pure(i)
    #:: ExpectedOutput(assert.failed:assertion.false)
    assert first == third, UNREACHABLE


#@ ensures: implies(success(), result() == simple(at).get_val())
@public
def get_simple_val(at: address) -> int128:
    return simple(at).get_val()


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: simple(at).get_val() == old(simple(at).get_val())
@public
def set_simple_val(at: address):
    simple(at).set_val(5)
