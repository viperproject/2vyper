
b: bool
i: int128
u: uint256

#@ invariant: not self.b
#@ invariant: self.i == 0

#:: ExpectedOutput(invariant.violated:assertion.false)
#@ invariant: self.u == 1

