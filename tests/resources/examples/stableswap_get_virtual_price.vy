# (c) Curve.Fi, 2020

#@ config: no_overflows

from vyper.interfaces import ERC20

N_COINS: constant(int128) = 3

LENDING_PRECISION: constant(uint256) = 10 ** 18
PRECISION: constant(uint256) = 10 ** 18

balances: public(uint256[N_COINS])
A: public(uint256)
token: ERC20

@private
@constant
def _xp() -> uint256[N_COINS]:
    result: uint256[N_COINS] = [convert(1, uint256), convert(1000000000000, uint256), convert(1000000000000, uint256)]
    for i in range(N_COINS):
        result[i] = result[i] * self.balances[i] / LENDING_PRECISION
    return result


#@ requires: y > 0
#@ lemma_def mul_div_same(x: uint256, y: uint256):
    #@ x * y / y == x * (y / y)
    #@ x * y / y == x * 1
    #@ x * y / y == x

#@ ensures: success() ==> forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> result() == N_COINS * xp[0]
@private
@constant
def get_D(xp: uint256[N_COINS]) -> uint256:
    S: uint256 = 0
    for _x in xp:
        S += _x
    if S == 0:
        return 0

    #@ lemma_assert interpreted(forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> S == N_COINS * xp[0])

    Dprev: uint256 = 0
    D: uint256 = S
    Ann: uint256 = self.A * N_COINS
    for _i in range(255):
        #@ invariant: S == old(S) and Ann == old(Ann)
        #@ invariant: forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> D == S
        D_P: uint256 = D
        #@ lemma_assert interpreted(_x * 2 == _x + _x) and interpreted(_x * 3 == _x + _x + _x)
        for _x in xp:
            #@ invariant: S == old(S) and D == old(D)
            #@ invariant: forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> D_P == D

            #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> _x == xp[0]
            #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> S == (_x * N_COINS)
            #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> D_P * D / (_x * N_COINS) == D_P * D / S
            #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> lemma.mul_div_same(D_P, D)
            #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> D_P * D / (_x * N_COINS) == D_P
            D_P = D_P * D / (_x * N_COINS)
        #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> D_P == D and D_P == S
        #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> (Ann * S + D_P * N_COINS)  == ((Ann - 1) * D + (N_COINS + 1) * D_P)
        #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> lemma.mul_div_same(D, (Ann * S + D_P * N_COINS))
        #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> (Ann * S + D_P * N_COINS) * D / ((Ann - 1) * D + (N_COINS + 1) * D_P) == D
        Dprev = D
        D = (Ann * S + D_P * N_COINS) * D / ((Ann - 1) * D + (N_COINS + 1) * D_P)
        #@ lemma_assert forall({i: uint256}, i < N_COINS ==> xp[0] == xp[i]) ==> Dprev == D
        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 1:
                break
        else:
            if Dprev - D <= 1:
                break
    return D



@public
@constant
def get_virtual_price() -> uint256:
    """
    Returns portfolio virtual price (for calculating profit)
    scaled up by 1e18
    """
    D: uint256 = self.get_D(self._xp())
    # D is in the units similar to DAI (e.g. converted to precision 1e18)
    # When balanced, D = n * x_u - total virtual value of the portfolio
    token_supply: uint256 = self.token.totalSupply()
    return D * PRECISION / token_supply
