
f: int128
owner: address

#@ invariant: implies(old(msg.sender) == self.owner, self.f == 0)


@public
def __init__():
    self.owner = msg.sender


@public
def owner_change():
    assert msg.sender == self.owner
    self.f = 0


@public
def non_owner_change():
    assert msg.sender != self.owner
    self.f = 1