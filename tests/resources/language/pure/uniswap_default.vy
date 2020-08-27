
# @title Uniswap Exchange Interface V1
# @notice Source code found at https://github.com/uniswap
# @notice Use at your own risk

#@ config: trust_casts, no_overflows

import tests.resources.language.pure.erc20_interface as ERC20

token: ERC20

#@pure
@private
@constant
def getInputPrice(input_amount: uint256, input_reserve: uint256, output_reserve: uint256) -> uint256:
    assert input_reserve > 0 and output_reserve > 0
    input_amount_with_fee: uint256 = input_amount * 997
    numerator: uint256 = input_amount_with_fee * output_reserve
    denominator: uint256 = (input_reserve * 1000) + input_amount_with_fee
    return numerator / denominator

@private
def ethToTokenInput(eth_sold: uint256(wei), min_tokens: uint256, deadline: timestamp, buyer: address, recipient: address) -> uint256:
    assert deadline >= block.timestamp and (eth_sold > 0 and min_tokens > 0)
    token_reserve: uint256 = self.token.balanceOf(self)
    tokens_bought: uint256 = self.getInputPrice(as_unitless_number(eth_sold), as_unitless_number(self.balance - eth_sold), token_reserve)
    assert tokens_bought >= min_tokens
    assert_modifiable(self.token.transfer(recipient, tokens_bought))
    return tokens_bought

#@ ensures: success() ==> forall({token_reserve: uint256}, token_reserve > 0 ==> \
    #@ old(result(self.getInputPrice(msg.value, self.balance, token_reserve))) \
    #@ >= result(self.getInputPrice(msg.value, self.balance, token_reserve)))
@public
@payable
def __default__():
    self.ethToTokenInput(msg.value, 1, block.timestamp, msg.sender, msg.sender)
