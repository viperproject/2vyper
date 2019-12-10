#
# The MIT License (MIT)
#
# Copyright (c) 2016 Kieran Elby
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


struct Monarch:
    addr: address
    name: string[256]
    claim_price: wei_value
    coronation_time: timestamp


ThroneClaimed: event({usurpur_addr: address, usurpur_name: string[256], new_claim_price: wei_value})


wizard: address

CLAIM_PRICE_ADJUST_NUM: constant(uint256) = 3
CLAIM_PRICE_ADJUST_DEN: constant(uint256) = 2

WIZARD_COMMISSION_FRACTION_NUM: constant(uint256) = 1
WIZARD_COMMISSION_FRACTION_DEN: constant(uint256) = 100

current_claim_price: wei_value
current_monarch: Monarch

pending_returns: map(address, wei_value)


#@ invariant: self.balance >= sum(self.pending_returns)
#@ invariant: forall({a: address, v: wei_value}, {accessible(a, v)}, v == self.pending_returns[a] ==> accessible(a, v))
#@ always check: self.current_monarch != old(self.current_monarch) ==> event(ThroneClaimed(self.current_monarch.addr, self.current_monarch.name, self.current_claim_price))
#@ always check: msg.value < old(self.current_claim_price) ==> self.current_monarch == old(self.current_monarch)


@public
def __init__(starting_claim_price: wei_value):
    self.wizard = msg.sender
    self.current_claim_price = starting_claim_price
    self.current_monarch = Monarch({addr: msg.sender, name: "<Vacant>", claim_price: 0, coronation_time: block.timestamp})


#@ ensures: success() ==> sent(msg.sender) >= old(sent(msg.sender) + self.pending_returns[msg.sender])
@public
def withdraw():
    amount: wei_value = self.pending_returns[msg.sender]
    self.pending_returns[msg.sender] = 0
    send(msg.sender, amount)


@public
@payable
def claim_throne(name: string[256]):
    value_paid: wei_value = msg.value

    assert value_paid == self.current_claim_price

    wizard_commission: wei_value = (value_paid * WIZARD_COMMISSION_FRACTION_NUM) / WIZARD_COMMISSION_FRACTION_DEN
    compensation: wei_value = value_paid - wizard_commission

    self.pending_returns[self.wizard] += wizard_commission

    if self.current_monarch.addr != self.wizard:
        self.pending_returns[self.current_monarch.addr] += compensation
    
    self.current_monarch = Monarch({addr: msg.sender, name: name, claim_price: value_paid, coronation_time: block.timestamp})
    self.current_claim_price = self.current_claim_price * CLAIM_PRICE_ADJUST_NUM / CLAIM_PRICE_ADJUST_DEN

    log.ThroneClaimed(self.current_monarch.addr, self.current_monarch.name, self.current_claim_price)
