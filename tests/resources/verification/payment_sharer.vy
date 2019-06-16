
splits: map(uint256, uint256)
deposits: map(uint256, wei_value)
first: map(uint256, address)
second: map(uint256, address)


@public
def initialize(id: uint256, _first: address, _second: address):
    assert self.first[id] == ZERO_ADDRESS and self.second[id] == ZERO_ADDRESS
    self.first[id] = _first
    self.second[id] = _second


@public
@payable
def deposit(id: uint256):
    self.deposits[id] += msg.value


@public
def updateSplit(id: uint256, split: uint256):
    assert split <= 100
    self.splits[id] = split

@public
def splitFunds(id: uint256):
    # Here would be: 
    # Signatures that both parties agree with this split

    # Split
    a: address = self.first[id]
    b: address = self.second[id]
    depo: uint256 = as_unitless_number(self.deposits[id])
    self.deposits[id] = 0

    first_am: uint256 = depo * self.splits[id] / 100
    second_am: uint256 = depo - first_am
    
    send(a, as_wei_value(first_am, "wei"))
    send(b, as_wei_value(second_am, "wei"))