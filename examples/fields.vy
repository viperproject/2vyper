
f1: int128
f2: int128
f3: bool
f4: uint256

#@ invariant: self.f1 == self.f2
#@ invariant: self.f3

@public
def foo():
    l1: int128 = self.f1

@public
def bar():
    self.f1 = 5