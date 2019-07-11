#
# The MIT License (MIT)
#
# Copyright (c) 2015 Vitalik Buterin
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

# This file was adapted from https://github.com/ethereum/vyper/blob/master/examples/auctions/simple_open_auction.vy


beneficiary: public(address)
auctionStart: public(timestamp)
auctionEnd: public(timestamp)

highestBidder: public(address)
highestBid: public(wei_value)

ended: public(bool)

pendingReturns: public(map(address, wei_value))


#@ invariant: implies(self.highestBidder == ZERO_ADDRESS, self.highestBid == 0)
#@ invariant: self.beneficiary == old(self.beneficiary)

#@ invariant: implies(old(self.ended), self.ended)

# always ensures: implies(block.timestamp < self.auctionEnd, not self.ended)
#@ invariant: implies(not self.ended, sum(self.pendingReturns) + self.highestBid <= self.balance)
#@ invariant: implies(not self.ended, sum(self.pendingReturns) + self.highestBid == sum(received()) - sum(sent()))
#@ invariant: implies(self.ended, sum(self.pendingReturns) <= self.balance)

#@ invariant: self.highestBid >= old(self.highestBid)
#@ invariant: implies(old(self.ended), self.highestBid == old(self.highestBid) and self.highestBidder == old(self.highestBidder))
#@ always ensures: implies(success() and msg.value > old(self.highestBid) and self.highestBidder != ZERO_ADDRESS, msg.sender == self.highestBidder)

#@ invariant: self.beneficiary != ZERO_ADDRESS
#@ invariant: self.highestBidder != self.beneficiary
#@ invariant: self.pendingReturns[self.beneficiary] == 0
#@ invariant: implies(not self.ended, sent(self.beneficiary) == 0)
#@ invariant: implies(self.ended, sent(self.beneficiary) == self.highestBid)

#@ invariant: sent(self.highestBidder) + self.highestBid + self.pendingReturns[self.highestBidder] == received(self.highestBidder)
#@ invariant: forall({a: address}, {received(a)}, implies(a != self.highestBidder and a != self.beneficiary, sent(a) + self.pendingReturns[a] == received(a)))

#@ invariant: sent(ZERO_ADDRESS) == 0
#@ invariant: forall({a: address}, {self.pendingReturns[a]}, implies(self.pendingReturns[a] != 0, received(a) != 0))
#@ invariant: forall({a: address}, {received(a)}, implies(a != self.beneficiary and received(a) == 0, sent(a) == 0))


@public
def __init__(_beneficiary: address, _bidding_time: timedelta):
    assert _beneficiary != ZERO_ADDRESS
    
    self.beneficiary = _beneficiary
    self.auctionStart = block.timestamp
    self.auctionEnd = self.auctionStart + _bidding_time


#@ ensures: implies(success(), self.highestBid > old(self.highestBid))
@public
@payable
def bid():
    assert block.timestamp < self.auctionEnd
    assert not self.ended
    assert msg.value > self.highestBid
    assert msg.sender != self.beneficiary

    self.pendingReturns[self.highestBidder] += self.highestBid
    self.highestBidder = msg.sender
    self.highestBid = msg.value


#@ ensures: success(-msg.sender)
@public
def withdraw():
    pending_amount: wei_value = self.pendingReturns[msg.sender]
    self.pendingReturns[msg.sender] = 0
    send(msg.sender, pending_amount)


#@ ensures: implies(not self.ended, sum(sent()) == old(sum(sent())))
@public
def endAuction():
    assert block.timestamp >= self.auctionEnd
    assert not self.ended

    self.ended = True

    send(self.beneficiary, self.highestBid)
