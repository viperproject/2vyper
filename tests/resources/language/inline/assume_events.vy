#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

contract C:
    def send(): modifying

Transfer: event({_from: indexed(address), _to: indexed(address), _value: uint256})

val: int128
ad: address
weis: uint256

ads: address[10]

#@ always check: self.val > old(self.val) ==> event(Transfer(msg.sender, self.ad, self.weis), 2)

# Require that the pre_state is the same as the last public state for self
#@ requires: storage(self) == public_old(storage(self))
# Require that an event is logged
#:: ExpectedOutput(precondition.violated:assertion.false, CALL)
#@ requires: event(Transfer(msg.sender, self.ad, self.weis), 1)
# self.val increased and we returned self.ad
#@ ensures: success() ==> self.val > public_old(self.val) and result() == self.ad
# An event is still logged
#@ ensures: event(Transfer(msg.sender, self.ad, self.weis), 1)
# self.ad and self.weis stayed the same
#@ ensures: self.ad == public_old(self.ad) and self.weis == public_old(self.weis)
# There should be no public state in this function
#@ check: False
@private
def inc_val() -> address:
    self.val += 1
    return self.ad

#@ requires: self.val > public_old(self.val)
#@ requires: event(Transfer(msg.sender, self.ad, self.weis), 2)
#@ ensures: success() ==> event(Transfer(_sender, _to, _amount), 2)
#@ ensures: success() ==> self.weis == _amount and self.ad == _to
#@ check: event(Transfer(msg.sender, self.ad, self.weis), 2)
@private
def transfer(_sender: address, _to: address, _amount: uint256):
    C(_sender).send()
    self.ad = _to
    self.weis = _amount
    log.Transfer(_sender, _to, _amount)
    log.Transfer(_sender, _to, _amount)

#@ check: success() ==> event(Transfer(msg.sender, self.ad, self.weis), 2)
@public
def transfer_stmts():
    log.Transfer(msg.sender, self.ad, self.weis)
    log.Transfer(msg.sender, self.inc_val(), self.weis)
    C(msg.sender).send()
    log.Transfer(msg.sender, self.ad, self.weis)
    temp: address = self.inc_val()
    log.Transfer(msg.sender, self.ad, self.weis)
    self.transfer(msg.sender, temp, self.weis)


#@ check: success() ==> event(Transfer(msg.sender, self.ad, self.weis), 3)
@public
def triple_event_fail():
    log.Transfer(msg.sender, self.ad, self.weis)
    log.Transfer(msg.sender, self.ad, self.weis)
    #:: Label(CALL)
    log.Transfer(msg.sender, self.inc_val(), self.weis)