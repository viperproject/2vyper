
i: int128

#@ invariant: self.i == 0
#:: ExpectedOutput(invariant.violated:assertion.false)
#@ invariant: self.i == 5