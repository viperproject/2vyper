# @title Uniswap Exchange Interface V1
# @notice Source code found at https://github.com/uniswap
# @notice Use at your own risk

#@ config: allocation, no_derived_wei_resource, trust_casts

#@ interface


import tests.resources.allocation.uniswap.IExchange_alloc as Exchange

#@ ghost:
    #@ def exchange_addr(token_addr: address) -> Exchange: ...

#@ invariant: forall({a: address}, old(exchange_addr(self, a)) != ZERO_ADDRESS ==> exchange_addr(self, a) == old(exchange_addr(self, a)))

#@ ensures: success() ==> result() == exchange_addr(self, token_addr)
@public
@constant
def getExchange(token_addr: address) -> address:
    raise "Not implemented"
