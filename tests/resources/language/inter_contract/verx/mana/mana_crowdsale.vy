#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ config: trust_casts

from . import mana_continuous_sale_interface
from . import mana_token_interface

token_address: address
token: mana_token_interface
continuousSale: mana_continuous_sale_interface
_init: bool

#@ invariant: self.token == old(self.token)
#@ invariant: self.continuousSale == old(self.continuousSale)
#@ invariant: self.token != self
#@ invariant: self.continuousSale != self
#@ invariant: self.continuousSale != self.token_address
#@ invariant: self.token == self.token_address
#@ invariant: old(self._init) ==> self._init

#@ inter contract invariant: self._init ==> mana_continuous_sale_interface.owner(self.continuousSale) == self
#@ inter contract invariant: self._init ==> token(self.continuousSale) == self.token
#@ inter contract invariant: not locked("lock") and self._init ==> not started(self.continuousSale) ==> \
    #@ mana_token_interface.owner(self.token) == self
#@ inter contract invariant: not locked("lock") and self._init ==> started(self.continuousSale) ==> \
    #@ mana_token_interface.owner(self.token) == self.continuousSale

@public
def __init__(a: address, b: address):
    assert not self._init
    assert a != b
    assert self != a
    assert self != b
    self.token_address = a
    self.token = mana_token_interface(a)
    self.continuousSale = mana_continuous_sale_interface(b)

    assert self.token.get_owner() == self
    assert self.continuousSale.get_owner() == self
    assert self.continuousSale.get_token() == self.token
    assert not self.continuousSale.is_started()
    self._init = True

@nonreentrant('lock')
@public
@payable
def beginContinuousSale():
    assert self._init
    assert not self.continuousSale.is_started()
    self.token.transferOwnership(self.continuousSale)
    self.continuousSale.start()
