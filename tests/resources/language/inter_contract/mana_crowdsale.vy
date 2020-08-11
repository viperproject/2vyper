#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: trust_casts

from . import mana_continuous_sale_interface
from . import mana_token_interface

token: mana_token_interface
continuousSale: mana_continuous_sale_interface
_init: bool

#@ invariant: self.token == old(self.token)
#@ invariant: self.token != self
#@ invariant: self.continuousSale == old(self.continuousSale)
#@ invariant: self.continuousSale != self
#@ invariant: old(self._init) ==> self._init

# inter contract invariant: not locked("lock") and self._init ==> not started(self.continuousSale) ==> token_owner(self.token) == self

@public
def __init__(a: address, b: address):
    assert not self._init
    assert self != a
    assert self != b
    self.token = mana_token_interface(a)
    self.continuousSale = mana_continuous_sale_interface(a)

    assert self.token.get_owner() == self
    assert self.continuousSale.get_owner() == self
    assert not self.continuousSale.is_started()
    self._init = True

@nonreentrant('lock')
@public
@payable
def start():
    assert self._init
    self.token.transferOwnership(self.continuousSale)
    self.continuousSale.start()
