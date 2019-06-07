
val: int128

@public
def __init__(a: int128, b: int128):
    self.val = a ** b


#@ ensures: result() >= 1
@public
def pow(a: uint256, b: uint256) -> uint256:
    return a ** b + 1