
units: {
    u: "unit"
}


iu: int128(u)
uu: uint256(u)

ius: int128(u)[9]
uus: uint256(u)[9]


#@ ensures: result() == a
@public
def test(a: int128(u), b: uint256(u)) -> int128(u):
    c: int128(u) = a
    d: int128(u**2) = c * a
    c = 12
    return a
