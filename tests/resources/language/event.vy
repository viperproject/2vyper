#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas, no_overflows


Transfer: event({_from: indexed(address), _to: indexed(address), _value: uint256})


val: int128
ad: address
weis: uint256

ads: address[10]


@public
def transfer(_to: address, _amount: uint256):
    log.Transfer(msg.sender, _to, _amount)


@private
def inc_val() -> address:
    self.val += 1
    return self.ad


#@ ensures: self.val == old(self.val) + 1
#@ check: event(Transfer(msg.sender, self.ad, self.weis), 1)
#@ check: event(Transfer(msg.sender, self.ad, self.weis))
@public
def transfer_stmts():
    log.Transfer(msg.sender, self.inc_val(), self.weis)


#@ ensures: revert()
@public
def transfer_not_success(idx: int128):
    assert idx > 10
    log.Transfer(msg.sender, self.ads[idx], self.weis)


#@ check: implies(0 <= idx and idx < 10, event(Transfer(msg.sender, self.ads[idx], self.weis), 2))
@public
def transfer_twice(idx: int128):
    log.Transfer(msg.sender, self.ads[idx], self.weis)
    log.Transfer(msg.sender, self.ads[idx], self.weis)


#@ ensures: revert()
#:: ExpectedOutput(check.violated:assertion.false)
#@ check: event(Transfer(msg.sender, self.ad, self.weis))
@public
def transfer_revert_fail(idx: int128):
    log.Transfer(msg.sender, self.ad, self.weis)
    assert False


#@ check: success() ==> self.val > old(self.val) ==> event(Transfer(msg.sender, self.ad, self.weis))
@public
def transfer_send(idx: int128):
    self.val += 1
    log.Transfer(msg.sender, self.ad, self.weis)
    send(msg.sender, self.balance)
    self.val += 1
    log.Transfer(msg.sender, self.ad, self.weis)


#@ check: success() ==> self.val > old(self.val) ==> event(Transfer(msg.sender, self.ad, self.weis))
@public
def transfer_conditional_send(idx: int128):
    self.val += 1
    log.Transfer(msg.sender, self.ad, self.weis)
    if idx > 12:
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)


#@ check: success() ==> self.val > old(self.val) ==> event(Transfer(msg.sender, self.ad, self.weis))
@public
def transfer_multiple_conditional_sends(idx: int128):
    self.val += 1
    log.Transfer(msg.sender, self.ad, self.weis)
    if idx > 12:
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)

    if idx > 18:
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)
    else:
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)

    if idx > 24:
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)


#:: ExpectedOutput(check.violated:assertion.false) 
#@ check: success() ==> self.val > old(self.val) ==> event(Transfer(msg.sender, self.ad, self.weis))
@public
def transfer_multiple_conditional_sends_fail(idx: int128):
    self.val += 1
    log.Transfer(msg.sender, self.ad, self.weis)
    if idx > 12:
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)

    if idx > 18:
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)
    else:
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)
        send(msg.sender, self.balance)
        self.val += 1
        # Forget to fire event

    if idx > 24:
        send(msg.sender, self.balance)
        self.val += 1
        log.Transfer(msg.sender, self.ad, self.weis)
