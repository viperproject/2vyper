#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: trust_casts

from . import mana_continuous_sale_interface
from . import mana_token_interface

implements: mana_continuous_sale_interface

started: bool
owner: address
token: mana_token_interface

#@ ghost:
    #@ @implements
    #@ def started() -> bool: self.started
    #@ @implements
    #@ def owner() -> address: self.owner
    #@ @implements
    #@ def token() -> address: self.token


@public
def __init__(o: address, t: address):
    self.owner = o
    self.token = mana_token_interface(t)
    self.started = False


@public
@constant
def get_owner() -> address:
    return self.owner


@public
@constant
def get_token() -> address:
    return self.token


@public
@constant
def is_started() -> bool:
    return self.started


@public
def start():
    assert self.owner == msg.sender
    assert not self.started
    self.started = True
