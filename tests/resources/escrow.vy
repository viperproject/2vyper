
buyer: address
seller: address
escrow: address

start: timestamp

buyerOk: bool
sellerOk: bool

ended: bool


@public
def __init__(buyer_address: address, seller_address: address):
    self.buyer = buyer_address
    self.seller = seller_address
    self.escrow = msg.sender
    self.start = block.timestamp


@private
@constant
def thirty_days_passed() -> bool:
    return block.timestamp > self.start + 2592000


@private
def pay_balance():
    send(self.escrow, self.balance / 100)
    send(self.seller, self.balance)


@public
def accept():
    if msg.sender == self.buyer:
        self.buyerOk = True
    elif msg.sender == self.seller:
        self.sellerOk = True
    
    if self.buyerOk and self.sellerOk:
        self.ended = True
        self.pay_balance()
    elif self.buyerOk and not self.sellerOk and self.thirty_days_passed():
        self.ended = True
        send(self.buyer, self.balance)


@public
@payable
def deposit():
    assert msg.sender == self.buyer


@public
def cancel():
    if msg.sender == self.buyer:
        self.buyerOk = False
    elif msg.sender == self.seller:
        self.sellerOk = False
    
    if not self.buyerOk and not self.sellerOk:
        send(self.buyer, self.balance)


@public
def kill():
    assert msg.sender == self.escrow
    self.ended = True
    send(self.buyer, self.balance)
