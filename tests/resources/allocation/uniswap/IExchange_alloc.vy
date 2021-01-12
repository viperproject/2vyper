# @title Uniswap Exchange Interface V1
# @notice Source code found at https://github.com/uniswap
# @notice Use at your own risk

#@ config: allocation, no_derived_wei_resource, trust_casts

#@ interface

import tests.resources.allocation.ERC20.IERC20_alloc as ERC20

#@ ghost:
    #@ def token() -> ERC20: ...
    #@ def balance() -> uint256: ...
    #@ def getInputPrice(input_amount: uint256, input_reserve: uint256, output_reserve: uint256) -> uint256: ...
    #@ def getOutputPrice(output_amount: uint256, input_reserve: uint256, output_reserve: uint256) -> uint256: ...

#@ invariant: old(token(self)) != ZERO_ADDRESS ==> token(self) == old(token(self))

#@ performs: reallocate[ERC20.token[token(self)]](getInputPrice(self, msg.value, balance(self), balanceOf(token(self))[self]), to=recipient, actor=self)
#@ ensures: old(token(self)) == ZERO_ADDRESS ==> revert()
@public
@payable
def ethToTokenTransferInput(min_tokens: uint256, deadline: timestamp, recipient: address) -> uint256:
    raise "Not implemented"

#@ performs: reallocate[Wei](msg.value - getOutputPrice(self, tokens_bought, balance(self), balanceOf(token(self))[self]), to=msg.sender, actor=self)
#@ performs: reallocate[ERC20.token[token(self)]](tokens_bought, to=recipient, actor=self)
#@ ensures: old(token(self)) == ZERO_ADDRESS ==> revert()
@public
@payable
def ethToTokenTransferOutput(tokens_bought: uint256, deadline: timestamp, recipient: address) -> uint256:
    raise "Not implemented"


#@ ensures: success() ==> result() == getOutputPrice(self, tokens_bought, balance(self), balanceOf(token(self))[self])
@public
@constant
def getEthToTokenOutputPrice(tokens_bought: uint256) -> uint256:
    raise "Not implemented"
