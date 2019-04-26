
#@ ensures: result() == 5
@public
def can_fail(amount: int128) -> int128:
    assert amount > 10
    return 5


#@ ensures: not success() or result() == 5
@public
def can_fail_as_well(amount: int128) -> int128:
    assert amount > 10
    return 5
