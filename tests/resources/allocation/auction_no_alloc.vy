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

# config: allocation

beneficiary: public(address)
auctionStart: public(timestamp)
auctionEnd: public(timestamp)

highestBidder: public(address)
highestBid: public(wei_value)

ended: public(bool)

pendingReturns: public(map(address, wei_value))

# resource: good()


#@ invariant: self.highestBidder == ZERO_ADDRESS ==> self.highestBid == 0
#@ invariant: self.beneficiary == old(self.beneficiary)
#@ invariant: self.beneficiary != ZERO_ADDRESS
#@ invariant: self.beneficiary != self.highestBidder
# new
# This invariant is newly needed
#@ invariant: self.highestBid == 0 ==> self.highestBidder == ZERO_ADDRESS

#@ invariant: old(self.ended) ==> self.ended

#@ invariant: self.pendingReturns[self.beneficiary] == 0
# invariant: forall({a: address}, {allocated(a)}, {self.pendingReturns[a]}, a != self.highestBidder ==> allocated(a) == self.pendingReturns[a])
#@ invariant: sent(self.beneficiary) == (self.highestBid if self.ended else 0)
# invariant: not self.ended ==> allocated(self.highestBidder) == self.highestBid + self.pendingReturns[self.highestBidder]
# invariant: self.ended ==> allocated(self.highestBidder) == self.pendingReturns[self.highestBidder]
# new
# Global leak check for resource "wei"
#@ invariant: forall({allocation_map: map(address, wei_value), fresh_allocation_map: map(address, wei_value)},
    # Assume invariants in a public state
    #@ (((forall({a: address}, a != self.highestBidder ==> allocation_map[a] == self.pendingReturns[a]))
        #@ and (not self.ended ==> allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
        #@ and (self.ended ==> allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder])) and
    # Assume invariants in a fresh (public) state
    #@ ((forall({a: address}, a != self.highestBidder ==> fresh_allocation_map[a] == self.pendingReturns[a]))
        #@ and (not self.ended ==> fresh_allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
        #@ and (self.ended ==> fresh_allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder]))) ==>
    # Perform leak check
    #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a]))
# This invariant is newly needed
#@ invariant: self.balance >= sum(self.pendingReturns) + (0 if self.ended else self.highestBid)


# invariant: not self.ended ==> forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.beneficiary else 0))
# invariant: self.ended ==> forall({a: address}, {allocated[good](a)}, allocated[good](a) == (1 if a == self.highestBidder else 0))
# new
# Global leak check for resource "good"
#@ invariant: forall({allocation_map: map(address, uint256), fresh_allocation_map: map(address, uint256)},
    # Assume invariants in a public state
    #@ (((not self.ended ==> forall({a: address}, allocation_map[a] == (1 if a == self.beneficiary else 0)))
        #@ and (self.ended ==> forall({a: address}, allocation_map[a] == (1 if a == self.highestBidder else 0)))) and
    # Assume invariants in a fresh (public) state
    #@ ((not self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.beneficiary else 0)))
        #@ and (self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.highestBidder else 0))))) ==>
    # Perform leak check
    #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a]))

# invariant: not self.ended ==> forall({a: address, v: wei_value}, {offered[good <-> wei](1, v, self.beneficiary, a)},
    # offered[good <-> wei](1, v, self.beneficiary, a) == 1)
# invariant: self.highestBidder != ZERO_ADDRESS and not self.ended ==> \
    # offered[wei <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary) >= 1

#@ invariant: forall({a: address}, accessible(a, self.pendingReturns[a]))

# performs: create[good](1, to=msg.sender)
# performs: foreach({a: address, v: wei_value}, offer[good <-> wei](1, v, to=a, times=1))
# new
# Local leak check for resource "wei"
#@ check: (success() ==>
    #@ forall({allocation_map: map(address, wei_value), pre_allocation_map: map(address, wei_value), fresh_allocation_map: map(address, wei_value)},
        # Assume invariants in last public state (There is no public state at the start of init.)
        #@ ((True) and
        # Assume the invariants in a fresh (public) state
        #@ ((forall({a: address}, a != self.highestBidder ==> fresh_allocation_map[a] == self.pendingReturns[a]))
            #@ and (not self.ended ==> fresh_allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
            #@ and (self.ended ==> fresh_allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder])) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        # No wei is allocated to anyone in init
        #@ (forall({a: address}, allocation_map[a] == 0))) ==>
        # Perform leak check
        #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a])))
# Local leak check for resource "good"
#@ check: (success() ==>
    #@ forall({allocation_map: map(address, wei_value), pre_allocation_map: map(address, wei_value), fresh_allocation_map: map(address, wei_value)},
        # Assume invariants in last public state (There is no public state at the start of init.)
        #@ ((True) and
        # Assume the invariants in a fresh (public) state
        #@ ((not self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.beneficiary else 0)))
            #@ and (self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.highestBidder else 0)))) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        #@ (forall({a: address}, allocation_map[a] == 0))
            # One "good" resource gets created for the self.beneficiary
            #@ and allocation_map[self.beneficiary] == 1) ==>
        # Perform leak check
        #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a])))
# Transformed offered[good <-> wei] invariant
#@ check: (success() ==>
    #@ forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256)))), pre_offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state (There is no public state at the start of init.)
        #@ ((True) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        # There were new offers made.
        #@ (forall({a: address, v: wei_value}, offered_map[msg.sender][a][1][v] == 1))) ==>
        # Check invariant about offered map
        #@ (not self.ended ==> forall({a: address, v: uint256}, offered_map[self.beneficiary][a][1][v] == 1))))
# Transformed offered[wei <-> good] invariant
#@ check: (success() ==>
    #@ forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256)))), pre_offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state (There is no public state at the start of init.)
        #@ ((True) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        # There were no changes to the offered[wei <-> good] map
        #@ (offered_map == pre_offered_map)) ==>
        # Check invariant about offered map
        #@ (self.highestBidder != ZERO_ADDRESS and not self.ended ==> offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] >= 1)))
@public
def __init__(_bidding_time: timedelta):    
    self.beneficiary = msg.sender
    self.auctionStart = block.timestamp
    self.auctionEnd = self.auctionStart + _bidding_time

    # create[good](1, to=self.beneficiary)
    # new
    # Trust check to perform offer
    #@ assert msg.sender == msg.sender, UNREACHABLE
    # foreach({a: address, v: wei_value}, offer[good <-> wei](1, v, to=a, times=1))


# performs: offer[wei <-> good](msg.value, 1, to=self.beneficiary, times=1)
# new
# Local leak check for resource "wei"
#@ check: (success() ==>
    #@ forall({allocation_map: map(address, wei_value), pre_allocation_map: map(address, wei_value), fresh_allocation_map: map(address, wei_value)},
        # Assume invariants in last public state
        #@ (old((forall({a: address}, a != self.highestBidder ==> pre_allocation_map[a] == self.pendingReturns[a]))
            #@ and (not self.ended ==> pre_allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
            #@ and (self.ended ==> pre_allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder])) and
        # Assume the invariants in a fresh (public) state
        #@ ((forall({a: address}, a != self.highestBidder ==> fresh_allocation_map[a] == self.pendingReturns[a]))
            #@ and (not self.ended ==> fresh_allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
            #@ and (self.ended ==> fresh_allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder])) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        #@ (forall({a: address}, a != msg.sender ==> allocation_map[a] == pre_allocation_map[a])
            # The received wei belongs to the msg.sender. (Information from the payable decorator.)
            #@ and allocation_map[msg.sender] == pre_allocation_map[msg.sender] + msg.value)) ==>
        # Perform leak check
        #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a])))
# Local leak check for resource "good"
#@ check: (success() ==>
    #@ forall({allocation_map: map(address, wei_value), pre_allocation_map: map(address, wei_value), fresh_allocation_map: map(address, wei_value)},
        # Assume invariants in last public state
        #@ (old((not self.ended ==> forall({a: address}, pre_allocation_map[a] == (1 if a == self.beneficiary else 0)))
            #@ and (self.ended ==> forall({a: address}, pre_allocation_map[a] == (1 if a == self.highestBidder else 0)))) and
        # Assume the invariants in a fresh (public) state
        #@ ((not self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.beneficiary else 0)))
            #@ and (self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.highestBidder else 0)))) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        # There were no changes to the "good" resource
        #@ (allocation_map == pre_allocation_map)) ==>
        # Perform leak check
        #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a])))
# Transformed offered[good <-> wei] invariant
#@ check: (success() ==>
    #@ forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256)))), pre_offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state
        #@ (old(not self.ended ==> forall({a: address, v: uint256}, pre_offered_map[self.beneficiary][a][1][v] == 1)) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        # There were no changes to the offered[good <-> wei] map
        #@ (offered_map == pre_offered_map)) ==>
        # Check invariant about offered map
        #@ (not self.ended ==> forall({a: address, v: uint256}, offered_map[self.beneficiary][a][1][v] == 1))))
# Transformed offered[wei <-> good] invariant
#@ check: (success() ==>
    #@ forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256)))), pre_offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state
        #@ (old(self.highestBidder != ZERO_ADDRESS and not self.ended ==> pre_offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] >= 1) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        #@ ((forall({a: address, o: address, v1: uint256, v2: uint256}, a != msg.sender or o != self.beneficiary or v1 != msg.value or v2 != 1 ==> offered_map[a][o][v1][v2] == pre_offered_map[a][o][v1][v2]))
            # There was a new offer from msg.sender to self.beneficiary.
            #@ and (offered_map[msg.sender][self.beneficiary][msg.value][1] == pre_offered_map[msg.sender][self.beneficiary][msg.value][1] + 1)) ==>
        # Check invariant about offered map
        #@ (self.highestBidder != ZERO_ADDRESS and not self.ended ==> offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] >= 1))))
@public
@payable
def bid():
    assert block.timestamp < self.auctionEnd
    assert not self.ended
    assert msg.value > self.highestBid
    assert msg.sender != self.beneficiary

    # new
    # Trust check to perform offer
    #@ assert msg.sender == msg.sender, UNREACHABLE
    # offer[wei <-> good](msg.value, 1, to=self.beneficiary, times=1)

    self.pendingReturns[self.highestBidder] += self.highestBid
    self.highestBidder = msg.sender
    self.highestBid = msg.value


# new
# Local leak check for resource "wei"
#@ check: (success() ==>
    #@ forall({allocation_map: map(address, wei_value), pre_allocation_map: map(address, wei_value), fresh_allocation_map: map(address, wei_value)},
        # Assume invariants in last public state
        #@ (old((forall({a: address}, a != self.highestBidder ==> pre_allocation_map[a] == self.pendingReturns[a]))
            #@ and (not self.ended ==> pre_allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
            #@ and (self.ended ==> pre_allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder])) and
        # Assume the invariants in a fresh (public) state
        #@ ((forall({a: address}, a != self.highestBidder ==> fresh_allocation_map[a] == self.pendingReturns[a]))
            #@ and (not self.ended ==> fresh_allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
            #@ and (self.ended ==> fresh_allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder])) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        #@ (forall({a: address}, a != msg.sender ==> allocation_map[a] == pre_allocation_map[a])
            # There is a send. (Due to reentrancy we cannot replace "self.pendingReturns[msg.sender]" with 0.)
            #@ and allocation_map[msg.sender] == self.pendingReturns[msg.sender]
                #@ + (0 if (msg.sender != self.highestBidder or self.ended) else self.highestBid))) ==>
        # Perform leak check
        #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a])))
# Local leak check for resource "good"
#@ check: (success() ==>
    #@ forall({allocation_map: map(address, wei_value), pre_allocation_map: map(address, wei_value), fresh_allocation_map: map(address, wei_value)},
        # Assume invariants in last public state
        #@ (old((not self.ended ==> forall({a: address}, pre_allocation_map[a] == (1 if a == self.beneficiary else 0)))
            #@ and (self.ended ==> forall({a: address}, pre_allocation_map[a] == (1 if a == self.highestBidder else 0)))) and
        # Assume the invariants in a fresh (public) state
        #@ ((not self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.beneficiary else 0)))
            #@ and (self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.highestBidder else 0)))) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        # There were no changes to the "good" resource
        #@ (allocation_map == pre_allocation_map)) ==>
        # Perform leak check
        #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a])))
# Transformed offered[good <-> wei] invariant
#@ check: (success() ==>
    #@ forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256)))), pre_offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state
        #@ (old(not self.ended ==> forall({a: address, v: uint256}, pre_offered_map[self.beneficiary][a][1][v] == 1)) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        # There were no changes to the offered[good <-> wei] map
        #@ (offered_map == pre_offered_map)) ==>
        # Check invariant about offered map
        #@ (not self.ended ==> forall({a: address, v: uint256}, offered_map[self.beneficiary][a][1][v] == 1))))
# Transformed offered[wei <-> good] invariant
#@ check: (success() ==>
    #@ forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256)))), pre_offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state
        #@ (old(self.highestBidder != ZERO_ADDRESS and not self.ended ==> pre_offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] >= 1) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        # There were no changes to the offered[good <-> wei] map
        #@ (offered_map == pre_offered_map)) ==>
        # Check invariant about offered map
        #@ (self.highestBidder != ZERO_ADDRESS and not self.ended ==> offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] >= 1)))
@public
def withdraw():
    pending_amount: wei_value = self.pendingReturns[msg.sender]
    self.pendingReturns[msg.sender] = 0
    send(msg.sender, pending_amount)


# new
# Local leak check for resource "wei"
#@ check: (success() ==>
    #@ forall({allocation_map: map(address, wei_value), pre_allocation_map: map(address, wei_value), fresh_allocation_map: map(address, wei_value)},
        # Assume invariants in last public state
        #@ (old((forall({a: address}, a != self.highestBidder ==> pre_allocation_map[a] == self.pendingReturns[a]))
            #@ and (not self.ended ==> pre_allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
            #@ and (self.ended ==> pre_allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder])) and
        # Assume the invariants in a fresh (public) state
        #@ ((forall({a: address}, a != self.highestBidder ==> fresh_allocation_map[a] == self.pendingReturns[a]))
            #@ and (not self.ended ==> fresh_allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
            #@ and (self.ended ==> fresh_allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder])) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        #@ (forall({a: address}, a != self.highestBidder and a != self.beneficiary ==> allocation_map[a] == pre_allocation_map[a])
            # The self.highestBidder has self.highestBid less wei allocated due to the exchange.
            # (Due to reentrancy we cannot replace "self.pendingReturns[msg.sender]" simply with the subtraction.)
            #@ and allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder]
            # All wei allocated to the self.beneficiary is sent to him.
            #@ and allocation_map[self.beneficiary] == 0)) ==>
        # Perform leak check
        #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a])))
# Local leak check for resource "good"
#@ check: (success() ==>
    #@ forall({allocation_map: map(address, wei_value), pre_allocation_map: map(address, wei_value), fresh_allocation_map: map(address, wei_value)},
        # Assume invariants in last public state
        #@ (old((not self.ended ==> forall({a: address}, pre_allocation_map[a] == (1 if a == self.beneficiary else 0)))
            #@ and (self.ended ==> forall({a: address}, pre_allocation_map[a] == (1 if a == self.highestBidder else 0)))) and
        # Assume the invariants in a fresh (public) state
        #@ ((not self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.beneficiary else 0)))
            #@ and (self.ended ==> forall({a: address}, fresh_allocation_map[a] == (1 if a == self.highestBidder else 0)))) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        #@ (forall({a: address}, a != self.beneficiary and a != self.highestBidder ==> allocation_map[a] == pre_allocation_map[a])
            # The exchange reduces the allocation of the good by one for the self.beneficiary.
            #@ and allocation_map[self.beneficiary] == pre_allocation_map[self.beneficiary] - 1
            # The exchange increases the allocation of the good by one for the self.highestBidder.
            #@ and allocation_map[self.highestBidder] == pre_allocation_map[self.highestBidder] + 1)) ==>
        # Perform leak check
        #@ forall({a: address}, allocation_map[a] == fresh_allocation_map[a])))
# Transformed offered[good <-> wei] invariant
#@ check: (success() ==>
    #@ forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256)))), pre_offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state
        #@ (old(not self.ended ==> forall({a: address, v: uint256}, pre_offered_map[self.beneficiary][a][1][v] == 1)) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        #@ ((forall({a: address, o: address, v1: uint256, v2: uint256}, a != msg.sender or o != self.beneficiary or v1 != msg.value or v2 != 1 ==> offered_map[a][o][v1][v2] == pre_offered_map[a][o][v1][v2]))
            # The exchange consumes one such offer.
            #@ and (offered_map[self.beneficiary][self.highestBidder][1][self.highestBid] == pre_offered_map[self.beneficiary][self.highestBidder][1][self.highestBid] - 1))) ==>
        # Check invariant about offered map
        #@ (not self.ended ==> forall({a: address, v: uint256}, offered_map[self.beneficiary][a][1][v] == 1))))
# Transformed offered[wei <-> good] invariant
#@ check: (success() ==>
    #@ forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256)))), pre_offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state
        #@ (old(self.highestBidder != ZERO_ADDRESS and not self.ended ==> pre_offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] >= 1) and
        # Create the current state from the pre_state and update the changes that would have happened in the resource system
        #@ ((forall({a: address, o: address, v1: uint256, v2: uint256}, a != msg.sender or o != self.beneficiary or v1 != msg.value or v2 != 1 ==> offered_map[a][o][v1][v2] == pre_offered_map[a][o][v1][v2]))
            # The exchange consumes one such offer.
            #@ and (offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] == pre_offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] - 1)) ==>
        # Check invariant about offered map
        #@ (self.highestBidder != ZERO_ADDRESS and not self.ended ==> offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] >= 1))))
@public
def endAuction():
    assert block.timestamp >= self.auctionEnd
    assert not self.ended

    self.ended = True

    # new
    # Check that there are enough offers[good <-> wei]
    #@ assert forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state
        #@ (old(not self.ended ==> forall({a: address, v: uint256}, offered_map[self.beneficiary][a][1][v] == 1))) ==>
        # Only check that there are enough offers if the offered amount and "times" are both non-zero
        #@ ((1 != 0) and (1 != 0)) ==>
        # Check that there are enough offers
        #@ (offered_map[self.beneficiary][self.highestBidder][1][self.highestBid] >= 1)), UNREACHABLE
    # Check that there are enough offers[wei <-> good]
    #@ assert forall({offered_map: map(address, map(address, map(uint256, map(uint256, uint256))))},
        # Assume invariants in last public state
        #@ (old(self.highestBidder != ZERO_ADDRESS and not self.ended ==> offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] >= 1)) ==>
        # Only check that there are enough offers if the offered amount and "times" are both non-zero
        #@ ((self.highestBid != 0) and (1 != 0)) ==>
        # Check that there are enough offers
        #@ (offered_map[self.highestBidder][self.beneficiary][self.highestBid][1] >= 1)), UNREACHABLE
    # Check that there are enough "wei" resource
    #@ assert forall({allocation_map: map(address, wei_value)},
        # Assume invariants in last public state
        #@ (old((forall({a: address}, a != self.highestBidder ==> allocation_map[a] == self.pendingReturns[a]))
            #@ and (not self.ended ==> allocation_map[self.highestBidder] == self.highestBid + self.pendingReturns[self.highestBidder])
            #@ and (self.ended ==> allocation_map[self.highestBidder] == self.pendingReturns[self.highestBidder]))) ==>
        # "Enough-resource" check
        #@ allocation_map[self.highestBidder] >= self.highestBid), UNREACHABLE
    # Check that there are enough "good" resource
    #@ assert forall({allocation_map: map(address, wei_value)},
        # Assume invariants in last public state
        #@ (old((not self.ended ==> forall({a: address}, allocation_map[a] == (1 if a == self.beneficiary else 0)))
            #@ and (self.ended ==> forall({a: address}, allocation_map[a] == (1 if a == self.highestBidder else 0))))) ==>
        # "Enough-resource" check
        #@ allocation_map[self.beneficiary] >= 1), UNREACHABLE
    # exchange[wei <-> good](self.highestBid, 1, self.highestBidder, self.beneficiary, times=1)

    send(self.beneficiary, self.highestBid)
