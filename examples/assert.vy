
f1: int128
f2: int128


#@ invariant: self.f1 > self.f2


#@ ensures: result() == 5
@public
def assert_true() -> int128:
    assert True
    return 5


@public
def set(value: int128):
    assert value > self.f2
    self.f1 = value