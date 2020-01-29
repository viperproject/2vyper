#
# The MIT License (MIT)
#
# Copyright (c) 2015 Vitalik Buterin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# Safe Remote Purchase
# Originally from
# https://github.com/ethereum/solidity/blob/develop/docs/solidity-by-example.rst
# Ported to vyper and optimized.

#@ config: allocation

OPEN: constant(int128) = 0
PURCHASED: constant(int128) = 1
ABORTED: constant(int128) = 2
RECEIVED: constant(int128) = 3

value: public(wei_value)
seller: public(address)
buyer: public(address)
state: public(int128)

pending_returns: public(map(address, wei_value))

#@ resource: good()

#@ invariant: self.seller == old(self.seller)
#@ invariant: old(self.buyer) != ZERO_ADDRESS ==> self.buyer == old(self.buyer)
#@ invariant: self.seller != self.buyer
#@ invariant: (self.state == OPEN or self.state == ABORTED) == (self.buyer == ZERO_ADDRESS)

#@ invariant: self.state in [OPEN, PURCHASED, ABORTED, RECEIVED]

#@ invariant: forall({a: address}, {allocated(a)}, a != self.buyer and a != self.seller ==> allocated(a) == 0)
#@ invariant: forall({a: address}, {self.pending_returns[a]}, a != self.buyer and a != self.seller ==> self.pending_returns[a] == 0)

#@ invariant: self.state in [OPEN, PURCHASED] ==> sum(self.pending_returns) == 0 and sum(sent()) == 0
#@ invariant: self.state in [OPEN, PURCHASED] ==> allocated(self.seller) == 2 * self.value
#@ invariant: self.state in [OPEN, ABORTED] ==> allocated(self.buyer) == 0
#@ invariant: self.state == PURCHASED ==> allocated(self.buyer) == 2 * self.value
#@ invariant: self.state in [ABORTED, RECEIVED] ==> \
    #@ forall({a: address}, {self.pending_returns[a]}, {allocated(a)}, self.pending_returns[a] == allocated(a))
#@ invariant: self.state == ABORTED ==> allocated(self.seller) == 2 * self.value and sent(self.seller) == 0 or (allocated(self.seller) == 0 and sent(self.seller) == 2 * self.value)
#@ invariant: self.state == RECEIVED ==> allocated(self.seller) == 3 * self.value and sent(self.seller) == 0 or (allocated(self.seller) == 0 and sent(self.seller) == 3 * self.value)
#@ invariant: self.state == RECEIVED ==> allocated(self.buyer) == self.value and sent(self.buyer) == 0 or (allocated(self.buyer) == 0 and sent(self.buyer) == self.value)

#@ invariant: self.state in [OPEN, ABORTED, PURCHASED] ==> forall({a: address}, {allocated[good](a)},
    #@ allocated[good](a) == (1 if a == self.seller else 0))
#@ invariant: self.state == RECEIVED ==> forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.buyer else 0))

#@ invariant: self.state in [OPEN, PURCHASED] ==> forall({a: address}, offered[good <-> wei](1, self.value, self.seller, a) == 1)
#@ invariant: self.state == PURCHASED ==> offered[wei <-> good](self.value, 1, self.buyer, self.seller) >= 1

#@ invariant: forall({a: address}, accessible(a, self.pending_returns[a]))

@public
@payable
def __init__():
    assert (msg.value % 2) == 0

    self.value = msg.value / 2
    self.seller = msg.sender
    self.state = OPEN

    #@ create[good](1)
    #@ foreach({a: address}, offer[good <-> wei](1, self.value, to=a, times=1))

@public
def withdraw():
    amount: wei_value = self.pending_returns[msg.sender]
    self.pending_returns[msg.sender] = 0
    send(msg.sender, amount)

@public
def abort():
    assert self.state == OPEN
    assert msg.sender == self.seller

    self.state = ABORTED
    self.pending_returns[self.seller] += 2 * self.value

    #@ foreach({a: address}, revoke[good <-> wei](1, self.value, to=a))

@public
@payable
def purchase():
    assert self.state == OPEN
    assert msg.value == (2 * self.value)
    assert msg.sender != self.seller

    self.state = PURCHASED
    self.buyer = msg.sender

    #@ offer[wei <-> good](self.value, 1, to=self.seller, times=1)

@public
def received():
    assert self.state == PURCHASED
    assert msg.sender == self.buyer

    self.state = RECEIVED

    #@ exchange[good <-> wei](1, self.value, self.seller, self.buyer, times=1)

    self.pending_returns[self.buyer] += self.value
    self.pending_returns[self.seller] += 3 * self.value
