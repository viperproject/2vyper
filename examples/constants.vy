
c1: constant(int128) = 12
c2: constant(int128) = 12 + 12 * 2 * 4 - 3
c3: constant(128) = 12 / 5
c4: constant(bool) = True and False and not True
c5: constant(bool) = not True or False or True
c6: constant(bool) = True and False


@public
def foo() -> int128:
    return c1 + c2

@public
def bar() -> int128:
    return c3

@public
def some() -> bool:
    b: bool = c6
    b = c5
    b = c4
    return b