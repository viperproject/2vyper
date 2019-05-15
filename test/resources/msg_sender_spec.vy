
f: int128
owner: address


#:: Label(FF)
#@ always ensures: implies(msg.sender == self.owner, self.f == 0)


@public
def __init__():
    self.owner = msg.sender


@public
def owner_change():
    assert msg.sender == self.owner
    self.f = 0


# This fails if self.owner calls it and self.f is already 1
#:: ExpectedOutput(postcondition.violated:assertion.false, FF)
@public
def non_owner_change():
    assert msg.sender != self.owner
    self.f = 1