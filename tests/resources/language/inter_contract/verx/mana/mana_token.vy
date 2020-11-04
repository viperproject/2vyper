#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import mana_token_interface
from . import mana_continuous_sale_interface

implements: mana_token_interface

owner: address

#@ ghost:
    #@ @implements
    #@ def owner() -> address: self.owner


@public
def __init__(o: address):
    self.owner = o


@public
@constant
def get_owner() -> address:
    return self.owner


@public
def transferOwnership(newOwner: address):
    assert msg.sender == self.owner
    self.owner = newOwner