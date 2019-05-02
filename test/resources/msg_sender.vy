
owner: address
b: bool

@public
def __init__():
    self.owner = msg.sender


#@ ensures: implies(msg.sender != self.owner, self.b == old(self.b))
@public
def set_b(new_value: bool):
    assert msg.sender == self.owner
    self.b = new_value