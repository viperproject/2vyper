#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import escrow_interface

implements: escrow_interface

state: uint256

deposits: map(address, uint256)

owner: address

#@ ghost:
    #@ @implements
    #@ def deposits() -> map(address, uint256): self.deposits
    #@ @implements
    #@ def refund_state() -> bool: self.state == 0
    #@ @implements
    #@ def success_state() -> bool: self.state == 1
    #@ @implements
    #@ def open_state() -> bool: self.state == 2
    #@ @implements
    #@ def owner() -> address: self.owner


@public
def __init__(o: address):
    self.owner = o
    self.state = 2


@public
@constant
def get_owner() -> address:
    return self.owner


@public
@constant
def is_open() -> bool:
    return self.state == 2


@public
@constant
def is_success() -> bool:
    return self.state == 1


@public
@constant
def is_refund() -> bool:
    return self.state == 0


@public
@payable
def deposit(p: address):
    self.deposits[p] += as_unitless_number(msg.value)


@public
def withdraw():
    assert self.state == 1
    send(msg.sender, self.balance)


@public
def claimRefund(p: address):
    assert self.state == 0
    val: uint256 = self.deposits[p]
    self.deposits[p] = 0
    send(p, val)


@public
def close():
    assert self.state == 2
    assert msg.sender == self.owner
    self.state = 1


@public
def refund():
    assert self.state == 2
    assert msg.sender == self.owner
    self.state = 0
