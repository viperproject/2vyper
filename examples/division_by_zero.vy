
#@ ensures: (b != 0) == success()
@public
def div(a: int128, b: int128) -> int128:
    return a / b