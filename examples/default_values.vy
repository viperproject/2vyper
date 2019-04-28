
b: bool
i: int128
u: uint256

#@ invariant: not self.b
#@ invariant: self.i == 0

# Will fail:
#@ invariant: self.u == 1

