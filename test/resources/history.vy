
counter: int128

#:: ExpectedOutput(invariant.violated:assertion.false)
#@ invariant: old(self.counter) <= self.counter

@public
def increment():
    self.counter += 1

@public
def decrease():
    self.counter -= 1