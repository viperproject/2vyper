
owner: address
b: bool


#@ invariant: self.owner == old(self.owner)
#@ invariant: implies(old(msg.sender) != self.owner, self.b == old(self.b))


@public
def __init__():
    self.owner = msg.sender


#@ ensures: implies(msg.sender != self.owner, self.b == old(self.b))
@public
def set_b(new_value: bool):
    assert msg.sender == self.owner
    self.b = new_value