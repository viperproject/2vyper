
counter: int128

#:: Label(INC)
#@ invariant: old(self.counter) <= self.counter

@public
def increment():
    self.counter += 1

#:: ExpectedOutput(invariant.violated:assertion.false, INC)
@public
def decrease():
    self.counter -= 1