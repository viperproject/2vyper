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

#@ config: allocation

beneficiary: public(address)
auctionStart: public(timestamp)
auctionEnd: public(timestamp)

highestBidder: public(address)
highestBid: public(wei_value)

ended: public(bool)

pendingReturns: public(map(address, wei_value))


#@ resource: good()


#@ invariant: self.highestBidder == ZERO_ADDRESS ==> self.highestBid == 0
#@ invariant: self.beneficiary == old(self.beneficiary)
#@ invariant: self.beneficiary != ZERO_ADDRESS
#@ invariant: self.beneficiary != self.highestBidder

#@ invariant: old(self.ended) ==> self.ended

#@ invariant: self.pendingReturns[self.beneficiary] == 0
#@ invariant: forall({a: address}, {allocated(a)}, {self.pendingReturns[a]}, a != self.highestBidder ==> allocated(a) == self.pendingReturns[a])
#@ invariant: sent(self.beneficiary) == (self.highestBid if self.ended else 0)
#@ invariant: not self.ended ==> allocated(self.highestBidder) == self.highestBid + self.pendingReturns[self.highestBidder]
#@ invariant: self.ended ==> allocated(self.highestBidder) == self.pendingReturns[self.highestBidder]

#@ invariant: not self.ended ==> forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.beneficiary else 0))
#@ invariant: self.ended ==> forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.highestBidder else 0))

#@ invariant: not self.ended ==> forall({a: address, v: wei_value}, {offered[good <-> wei](1, v, self.beneficiary, a)},
    #@ offered[good <-> wei](1, v, self.beneficiary, a) == 1)
#@ invariant: self.highestBidder != ZERO_ADDRESS and not self.ended ==> \
    #@ offered[wei <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary) >= 1

#@ invariant: forall({a: address}, accessible(a, self.pendingReturns[a]))

#@ invariant: not self.ended ==> allowed_to_liquidate[wei](self.beneficiary) == MAX_UINT256


@public
def __init__(_bidding_time: timedelta):    
    self.beneficiary = msg.sender
    self.auctionStart = block.timestamp
    self.auctionEnd = self.auctionStart + _bidding_time

    #@ create[good](1, to=self.beneficiary)
    #@ foreach({a: address, v: wei_value}, offer[good <-> wei](1, v, to=a, times=1))
    #@ allow_to_liquidate[wei](MAX_UINT256, self.beneficiary)


#@ performs: payable[wei](msg.value)
#@ performs: offer[wei <-> good](msg.value, 1, to=self.beneficiary, times=1)
@public
@payable
def bid():
    assert block.timestamp < self.auctionEnd
    assert not self.ended
    assert msg.value > self.highestBid
    assert msg.sender != self.beneficiary

    #@ offer[wei <-> good](msg.value, 1, to=self.beneficiary, times=1)

    self.pendingReturns[self.highestBidder] += self.highestBid
    self.highestBidder = msg.sender
    self.highestBid = msg.value


#@ performs: payout[wei](self.pendingReturns[msg.sender])
@public
def withdraw():
    pending_amount: wei_value = self.pendingReturns[msg.sender]
    self.pendingReturns[msg.sender] = 0
    send(msg.sender, pending_amount)


#@ performs: exchange[wei <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary, times=1)
#@ performs: payout[wei](self.highestBid, actor=self.beneficiary)
@public
def endAuction():
    assert block.timestamp >= self.auctionEnd
    assert not self.ended

    self.ended = True

    #@ exchange[wei <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary, times=1)

    send(self.beneficiary, self.highestBid)
