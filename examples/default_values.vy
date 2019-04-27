
b: bool
i: int128
u: uint256

#@ invariant: not self.b
#@ invariant: self.i == 0
#@ invariant: self.u == 0

@public
def __init__():
    pass