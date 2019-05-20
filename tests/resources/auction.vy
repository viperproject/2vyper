
beneficiary: public(address)
auctionStart: public(timestamp)
auctionEnd: public(timestamp)

highestBidder: public(address)
highestBid: public(wei_value)

ended: public(bool)

pendingReturns: public(map(address, wei_value))


#@ invariant: implies(self.highestBidder == ZERO_ADDRESS, self.highestBid == 0)
#@ invariant: self.beneficiary == old(self.beneficiary)

#@ invariant: implies(block.timestamp < self.auctionEnd, not self.ended)
#@ invariant: implies(not self.ended, sum(self.pendingReturns) + self.highestBid <= self.balance)
#@ invariant: implies(not self.ended, sum(self.pendingReturns) + self.highestBid == sum(received()) - sum(sent()))
#@ invariant: implies(self.ended, sum(self.pendingReturns) <= self.balance)

#@ invariant: self.highestBid >= old(self.highestBid)
#@ invariant: implies(self.ended, self.highestBid == old(self.highestBid) and self.highestBidder == old(self.highestBidder))
#@ always ensures: implies(success() and msg.value > old(self.highestBid) and self.highestBidder != ZERO_ADDRESS, msg.sender == self.highestBidder)

#@ invariant: implies(old(self.ended), self.ended)

#@ invariant: self.beneficiary != ZERO_ADDRESS
#@ invariant: self.highestBidder != self.beneficiary
#@ invariant: self.pendingReturns[self.beneficiary] == 0
#@ invariant: implies(not self.ended, sent(self.beneficiary) == 0)
#@ invariant: implies(self.ended, sent(self.beneficiary) == self.highestBid)

#@ invariant: sent(self.highestBidder) + self.highestBid + self.pendingReturns[self.highestBidder] == received(self.highestBidder)
#@ invariant: forall({a: address}, {received(a)}, implies(a != self.highestBidder and a != self.beneficiary, sent(a) + self.pendingReturns[a] == received(a)))


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
    assert msg.value > self.highestBid
    assert msg.sender != self.beneficiary

    self.pendingReturns[self.highestBidder] += self.highestBid
    self.highestBidder = msg.sender
    self.highestBid = msg.value


#@ ensures: implies(self.balance <= old(self.balance), self.balance - old(self.balance) <= old(self.pendingReturns[msg.sender]))
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
