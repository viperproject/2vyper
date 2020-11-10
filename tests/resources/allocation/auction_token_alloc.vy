#:: IgnoreFile(0)

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

import tests.resources.allocation.ERC20_alloc_interface as ERC20

#@ config: allocation

beneficiary: public(address)
auctionStart: public(timestamp)
auctionEnd: public(timestamp)

highestBidder: public(address)
highestBid: public(uint256)

ended: public(bool)

pendingReturns: public(map(address, uint256))

token: ERC20


#@ resource: good()
#@ meta resource: token() -> ERC20.token[self.token]


#@ invariant: self.highestBidder == ZERO_ADDRESS ==> self.highestBid == 0
#@ invariant: self.beneficiary == old(self.beneficiary)
#@ invariant: self.beneficiary != ZERO_ADDRESS
#@ invariant: self.beneficiary != self.highestBidder

#@ invariant: old(self.ended) ==> self.ended

#@ invariant: self.pendingReturns[self.beneficiary] == 0
#@ invariant: forall({a: address}, allocated(a) == 0)  # NEW: We have to deal with the WEI resource
#@ invariant: forall({a: address}, {allocated[token](a)}, {self.pendingReturns[a]}, a != self.highestBidder ==> allocated[token](a) == self.pendingReturns[a])
# invariant: sent(self.beneficiary) == (self.highestBid if self.ended else 0)  # This is not possible to write!
#@ invariant: not self.ended ==> allocated[token](self.highestBidder) == self.highestBid + self.pendingReturns[self.highestBidder]
#@ invariant: self.ended ==> allocated[token](self.highestBidder) == self.pendingReturns[self.highestBidder]

#@ invariant: not self.ended ==> forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.beneficiary else 0))
#@ invariant: self.ended ==> forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.highestBidder else 0))

#@ invariant: not self.ended ==> forall({a: address, v: wei_value}, {offered[good <-> token](1, v, self.beneficiary, a)},
    #@ offered[good <-> token](1, v, self.beneficiary, a) == 1)
#@ invariant: self.highestBidder != ZERO_ADDRESS and not self.ended ==> \
    #@ offered[token <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary) >= 1

# invariant: forall({a: address}, accessible(a, self.pendingReturns[a]))  # This is not possible to write!


# TODO:
# - Do meta resources have to have the same arguments as their underlying resource?
# - sent, received and accessible is only available for WEI!
# - We have to guarantee that this contract does not trust anyone on the token contract since it has a meta token there.
# - How to handle "allocate untracked x"?
#     - Allocate "allocated[underlying resource](self) - sum(allocated[meta resource])" to caller
#     => E.g. allocate "allocated[ERC20.token[self.token]](self) - sum(allocated[token])" to msg.sender
# - How to handle offers?
#     - Is an offer a new meta-meta-resource?
#     -> No, we cannot track this. Anyone can execute the exchange.
#     - Make a check that there is always enough resource amount to cover all offers?
#     - Assume at each public state that any amount of offers were executed?
#     => Do not allow offers.
# => Only allow reallocate, create, destroy, "allocate untracked x" with the self address as the source address in a resource function of the underlying token resource.
# -> Do we have to add Viper assertions that the trusted map and offered map stays zero for self on the underlying resource contract?
#
# -> We should havoc the allocated, offered, trusted map for all other contracts, when we havoc the contracts map.




#@ performs: create[good](1, to=msg.sender)
#@ performs: foreach({a: address, v: wei_value}, offer[good <-> token](1, v, to=a, times=1))
@public
def __init__(_bidding_time: timedelta):    
    self.beneficiary = msg.sender
    self.auctionStart = block.timestamp
    self.auctionEnd = self.auctionStart + _bidding_time

    #@ create[good](1, to=self.beneficiary)
    #@ foreach({a: address, v: wei_value}, offer[good <-> token](1, v, to=a, times=1))


#@ performs: offer[token <-> good](value, 1, to=self.beneficiary, times=1)
#@ performs: payable?[ERC20.token[self.token]](value)
@public
def bid(value: uint256):
    assert block.timestamp < self.auctionEnd
    assert not self.ended
    assert value > self.highestBid
    assert msg.sender != self.beneficiary

    # This should reallocate ERC20 tokens to this contract and allocate meta resources for the msg.sender
    self.token.transferFrom(msg.sender, self, value)

    #@ offer[token <-> good](value, 1, to=self.beneficiary, times=1)

    self.pendingReturns[self.highestBidder] += self.highestBid
    self.highestBidder = msg.sender
    self.highestBid = value


@public
def withdraw():
    pending_amount: uint256 = self.pendingReturns[msg.sender]
    self.pendingReturns[msg.sender] = 0
    # Deallocate the tokens
    self.token.transfer(msg.sender, pending_amount)


@public
def endAuction():
    assert block.timestamp >= self.auctionEnd
    assert not self.ended

    self.ended = True

    #@ exchange[token <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary, times=1)

    # Deallocate the exchanged tokens
    self.token.transfer(self.beneficiary, self.highestBid)
