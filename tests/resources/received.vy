
owner: address

balanceOf: map(address, wei_value)


#@ invariant: received(self.owner) == 0
#@ invariant: sum(self.balanceOf) == sum(received())


@public
def __init__():
    self.owner = msg.sender


@public
@payable
def pay():
    assert msg.sender != self.owner
    self.balanceOf[msg.sender] += msg.value

