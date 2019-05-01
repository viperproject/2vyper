
#@ invariant: True

#@ requires: i > 0
#@ ensures: result() == i + j
#@ ensures: old(i) == i
#@ ensures: old(j) == j
@public
def foo(i: int128, j: int128) -> int128:
    return i + j

#@ requires: i > 0
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() > 0
@public
@constant
def bar(i: int128) -> int128:
    return -i