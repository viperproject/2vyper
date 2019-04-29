
#@ ensures: (b != 0) == success()
@public
def div(a: int128, b: int128) -> int128:
    return a / b

# This should fail because the specification is not well formed
#@ ensures: result() == 5 / n
@public
def div_in_spec(n: int128) -> int128:
    if n != 0:
        return 5 / n
    else:
        return 0