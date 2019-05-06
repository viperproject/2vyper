
ZERO: constant(int128) = 0


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() == ZERO
@public
def one() -> int128:
    return 1


#:: ExpectedOutput(not.wellformed:division.by.zero)
#@ ensures: result() == 1 / ZERO
@public
def div_by_ZERO() -> int128:
    a: int128 = 1 / ZERO
    return a