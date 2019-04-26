
f1: int128
f2: int128
f3: int128

b1: bool
b2: bool

#@ invariant: self.b1 or self.f1 == self.f2
#@ invariant: self.f3 == 42


@public
def __init__():
    self.f3 = 42
    self.b1 = True


@public
def if_fail():
    assert self.f1 != self.f2
    self.f1 = 10
    self.f2 = 10
    self.b1 = False


@public
def if_fail_2():
    self.f3 = 12
    assert False


@public
def if_fail_3():
    self.b1 = True
    self.f3 = 14
    if self.b1:
        self.f3 = 42
    elif self.f1 == self.f2:
        assert not self.b1
