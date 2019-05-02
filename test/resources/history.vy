
counter: int128

#:: ExpectedOutput(invariant.violated:assertion.false, DEC)
#@ invariant: old(self.counter) <= self.counter

@public
def increment():
    self.counter += 1

#:: Label(DEC)
@public
def decrease():
    self.counter -= 1