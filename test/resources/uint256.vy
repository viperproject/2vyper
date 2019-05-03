
ui: uint256
mp: map(int128, uint256)

#@ ensures: self.ui >= 0
@public
def simple():
    pass

#@ ensures: result() >= 0
@public
def calc() -> uint256:
    return self.mp[100]

#@ ensures: result() >= 0
@public
def args(arg: uint256) -> uint256:
    return arg

#@ ensures: result() >= 0
@public
def add(a: uint256, b: uint256) -> uint256:
    return a + b * a + a * b

#@ ensures: success()
@public
def div(a: uint256, b: uint256) -> uint256:
    return a / (b + 1)

#@ ensures: not success()
@public
def fail(a: uint256, b: uint256) -> uint256:
    assert a > b
    self.ui = b - a