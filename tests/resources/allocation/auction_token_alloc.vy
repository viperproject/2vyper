#:: IgnoreFile(silicon)(0)

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

import tests.resources.allocation.ERC1363.IERC1363_alloc as ERC20
import tests.resources.allocation.ERC1363.IERC1363Spender_alloc as ERC1363Spender

#@ config: allocation, no_derived_wei_resource, trust_casts

implements: ERC1363Spender

beneficiary: public(address)
auctionStart: public(timestamp)
auctionEnd: public(timestamp)

highestBidder: public(address)
highestBid: public(uint256)

ended: public(bool)

pendingReturns: public(map(address, uint256))

token: ERC20


#@ resource: good()
#@ derived resource: token() -> ERC20.token[self.token]


#@ invariant: self.highestBidder == ZERO_ADDRESS ==> self.highestBid == 0
#@ invariant: self.beneficiary == old(self.beneficiary)
#@ invariant: self.beneficiary != ZERO_ADDRESS
#@ invariant: self.beneficiary != self.highestBidder

#@ invariant: old(self.ended) ==> self.ended

#@ invariant: self.pendingReturns[self.beneficiary] == 0
#@ invariant: forall({a: address}, {allocated[token](a)}, {self.pendingReturns[a]}, a != self.highestBidder ==> allocated[token](a) == self.pendingReturns[a])
#@ invariant: not self.ended ==> allocated[token](self.highestBidder) == self.highestBid + self.pendingReturns[self.highestBidder]
#@ invariant: self.ended ==> allocated[token](self.highestBidder) == self.pendingReturns[self.highestBidder]

#@ invariant: not self.ended ==> forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.beneficiary else 0))
#@ invariant: self.ended ==> forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.highestBidder else 0))

#@ invariant: not self.ended ==> forall({a: address, v: wei_value}, {offered[good <-> token](1, v, self.beneficiary, a)},
    #@ offered[good <-> token](1, v, self.beneficiary, a) == 1)
#@ invariant: self.highestBidder != ZERO_ADDRESS and not self.ended ==> \
    #@ offered[token <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary) >= 1

#@ invariant: not self.ended ==> allowed_to_decompose[token](self.beneficiary) == MAX_UINT256

#@ invariant: forall({a: address}, trusted(self.token, by=a))

@public
def __init__(_bidding_time: timedelta, token_address: address):
    assert token_address != self

    self.beneficiary = msg.sender
    self.auctionStart = block.timestamp
    self.auctionEnd = self.auctionStart + _bidding_time
    self.token = ERC20(token_address)

    #@ create[good](1, to=self.beneficiary)
    #@ foreach({a: address, v: wei_value}, offer[good <-> token](1, v, to=a, times=1))
    #@ assert no_offers[ERC20.token[self.token]](self), UNREACHABLE
    #@ allow_to_decompose[token](MAX_UINT256, msg.sender)

    #@ foreach({a: address}, trust(self.token, True, actor=a))


#@ performs: offer[token <-> good](value, 1, to=self.beneficiary, times=1)
#@ performs: payable[token](value)
@public
def bid(value: uint256):
    assert msg.sender != self
    assert msg.sender != self.beneficiary
    assert block.timestamp < self.auctionEnd
    assert not self.ended
    assert value > self.highestBid

    self.pendingReturns[self.highestBidder] += self.highestBid
    self.highestBidder = msg.sender
    self.highestBid = value

    #@ offer[token <-> good](value, 1, to=self.beneficiary, times=1)

    self.token.transferFrom(msg.sender, self, value)


#@ performs: offer[token <-> good](amount, 1, to=self.beneficiary, times=1, actor=sender)
#@ performs: payable[token](amount, actor=sender)
@public
def onApprovalReceived(sender: address, amount: uint256, data: bytes[1024]) -> bytes32:
    assert msg.sender == self.token
    assert msg.sender != self.beneficiary
    assert sender != self.beneficiary
    assert sender != ZERO_ADDRESS
    assert sender != self
    assert block.timestamp < self.auctionEnd
    assert not self.ended
    assert amount > self.highestBid

    self.pendingReturns[self.highestBidder] += self.highestBid
    self.highestBidder = sender
    self.highestBid = amount

    #@ offer[token <-> good](amount, 1, to=self.beneficiary, times=1, actor=sender)

    self.token.transferFrom(sender, self, amount)
    return 0x000000000000000000000000000000000000000000000000000000007b04a2d0


#@ performs: allow_to_decompose[token](self.pendingReturns[msg.sender], msg.sender)
#@ performs: payout[token](self.pendingReturns[msg.sender], actor=msg.sender)
@public
def withdraw():
    assert msg.sender != self and msg.sender != self.beneficiary
    pending_amount: uint256 = self.pendingReturns[msg.sender]
    self.pendingReturns[msg.sender] = 0
    #@ allow_to_decompose[token](pending_amount, msg.sender)

    # Deallocate the tokens
    self.token.transfer(msg.sender, pending_amount)


#@ performs: payout[token](self.highestBid, actor=self.beneficiary)
#@ performs: exchange[token <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary, times=1)
@public
def endAuction():
    assert self.beneficiary != self
    assert block.timestamp >= self.auctionEnd
    assert not self.ended

    self.ended = True

    #@ exchange[token <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary, times=1)

    # Deallocate the exchanged tokens
    self.token.transfer(self.beneficiary, self.highestBid)
