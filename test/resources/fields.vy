
f1: int128
f2: int128
f3: bool
f4: uint256

#:: ExpectedOutput(invariant.violated:assertion.false, BB)
#@ invariant: self.f1 == self.f2
#@ invariant: self.f3


@public
def __init__():
    self.f1 = 4
    self.f2 = self.f1
    self.f3 = not False

@public
def foo():
    l1: int128 = self.f1

#:: Label(BB)
@public
def bar():
    self.f1 = 5