#:: IgnoreFile(0)

# @title Uniswap Exchange Interface V1
# @notice Source code found at https://github.com/uniswap
# @notice Use at your own risk

#@ ghost:
    def balanceOf(addr: address) -> uint256: ...
from vyper.interfaces import ERC20

struct EtherTokenPair:
    _ether: uint256(wei)
    _token: uint256

# TODO: public constant functions to ghost functions

contract Factory:
    #@ ghost:
        #@ def getExchange(token_addr: address) -> address: ...
    def getExchange(token_addr: address) -> address: constant

contract Exchange:
    #@ ghost:
        #@ def token() -> address: ...
        #@ def getEthToTokenInputPrice(eth_sold: uint256(wei)) -> uint256: ...
        #@ def getEthToTokenOutputPrice(tokens_bought: uint256) -> uint256(wei): ...
    def getEthToTokenOutputPrice(tokens_bought: uint256) -> uint256(wei): constant
    def ethToTokenTransferInput(min_tokens: uint256, deadline: timestamp, recipient: address) -> uint256: modifying
    def ethToTokenTransferOutput(tokens_bought: uint256, deadline: timestamp, recipient: address) -> uint256(wei): modifying

TokenPurchase: event({buyer: indexed(address), eth_sold: indexed(uint256(wei)), tokens_bought: indexed(uint256)})
EthPurchase: event({buyer: indexed(address), tokens_sold: indexed(uint256), eth_bought: indexed(uint256(wei))})
AddLiquidity: event({provider: indexed(address), eth_amount: indexed(uint256(wei)), token_amount: indexed(uint256)})
RemoveLiquidity: event({provider: indexed(address), eth_amount: indexed(uint256(wei)), token_amount: indexed(uint256)})
Transfer: event({_from: indexed(address), _to: indexed(address), _value: uint256})
Approval: event({_owner: indexed(address), _spender: indexed(address), _value: uint256})

name: public(bytes32)                             # Uniswap V1
symbol: public(bytes32)                           # UNI-V1
decimals: public(uint256)                         # 18
totalSupply: public(uint256)                      # total number of UNI in existence
balances: map(address, uint256)                   # UNI balance of an address
allowances: map(address, map(address, uint256))   # UNI allowance of one address on another
token: ERC20                                      # address of the ERC20 token traded on this contract
factory: Factory                                  # interface for the factory that created this contract

#@ resource: UNI()

#@ invariant: old(self.factory) != ZERO_ADDRESS ==> self.factory == old(self.factory)
#@ invariant: old(self.factory) != ZERO_ADDRESS ==> self.token == old(self.token)

#@ invariant: forall({a: address}, allocated(a) == sum(allocated()) if a == self 0)
#@ invariant: allocated[UNI]() == balances(self)
#@ invariant: forall({a: address}, allocated[creator(UNI)](a) == 1)

#@ invariant: forall({o: address, s: address}, self.allowances[o][s] == offered[UNI <-> UNI](1, 0, o, s))

# TODO: There was no __init__ function...
#@ performs: foreach({a: address}, create[creator(UNI)](1, to=a))
@public
def __init__():
    pass
    #@ foreach({a: address}, create[creator(UNI)](1, to=a))

# @dev This function acts as a contract constructor which is not currently supported in contracts deployed
#      using create_with_code_of(). It is called once by the factory during contract creation.
@public
def setup(token_addr: address):
    assert (self.factory == ZERO_ADDRESS and self.token == ZERO_ADDRESS) and token_addr != ZERO_ADDRESS
    self.factory = Factory(msg.sender)
    self.token = ERC20(token_addr)
    self.name = 0x556e697377617020563100000000000000000000000000000000000000000000
    self.symbol = 0x554e492d56310000000000000000000000000000000000000000000000000000
    self.decimals = 18

# @notice Deposit ETH and Tokens (self.token) at current ratio to mint UNI tokens.
# @dev min_liquidity does nothing when total UNI supply is 0.
# @param min_liquidity Minimum number of UNI sender will mint if total UNI supply is greater than 0.
# @param max_tokens Maximum number of tokens deposited. Deposits max amount if total UNI supply is 0.
# @param deadline Time after which this transaction can no longer be executed.
# @return The amount of UNI minted.
#@ performs: reallocate(msg.value, to=self)
# FIXME: ?token_amount? == msg.value * balanceOf(self.token, self) / self.balance + 1
#@ performs: reallocate[token[self.token]](max_tokens if self.totalSupply == 0 else ?token_amount?, to=self)
# FIXME: ?liquidity_minted? == msg.value * self.totalSupply / self.balance
#@ performs: create[UNI](self.balance if self.totalSupply == 0 else ?liquidity_minted?)
#@ performs: allocate_untracked_wei(self)
@public
@payable
def addLiquidity(min_liquidity: uint256, max_tokens: uint256, deadline: timestamp) -> uint256:
    assert deadline > block.timestamp and (max_tokens > 0 and msg.value > 0)
    total_liquidity: uint256 = self.totalSupply
    #@ allocate_untracked_wei(self)
    if total_liquidity > 0:
        assert min_liquidity > 0
        #@ reallocate(msg.value, to=self)
        eth_reserve: uint256(wei) = self.balance - msg.value
        token_reserve: uint256 = self.token.balanceOf(self)
        token_amount: uint256 = msg.value * token_reserve / eth_reserve + 1
        liquidity_minted: uint256 = msg.value * total_liquidity / eth_reserve
        assert max_tokens >= token_amount and liquidity_minted >= min_liquidity
        self.balances[msg.sender] += liquidity_minted
        #@ create[UNI](liquidity_minted)
        self.totalSupply = total_liquidity + liquidity_minted
        assert_modifiable(self.token.transferFrom(msg.sender, self, token_amount))
        log.AddLiquidity(msg.sender, msg.value, token_amount)
        log.Transfer(ZERO_ADDRESS, msg.sender, liquidity_minted)
        return liquidity_minted
    else:
        assert (self.factory != ZERO_ADDRESS and self.token != ZERO_ADDRESS) and msg.value >= 1000000000
        assert self.factory.getExchange(self.token) == self
        #@ reallocate(msg.value, to=self)
        token_amount: uint256 = max_tokens
        initial_liquidity: uint256 = as_unitless_number(self.balance)
        self.totalSupply = initial_liquidity
        self.balances[msg.sender] = initial_liquidity
        #@ create[UNI](liquidity_minted)
        assert_modifiable(self.token.transferFrom(msg.sender, self, token_amount))
        log.AddLiquidity(msg.sender, msg.value, token_amount)
        log.Transfer(ZERO_ADDRESS, msg.sender, initial_liquidity)
        return initial_liquidity

# @dev Burn UNI tokens to withdraw ETH and Tokens at current ratio.
# @param amount Amount of UNI burned.
# @param min_eth Minimum ETH withdrawn.
# @param min_tokens Minimum Tokens withdrawn.
# @param deadline Time after which this transaction can no longer be executed.
# @return The amount of ETH and Tokens withdrawn.
# FIXME: ?eth_amount? == amount * self.balance / self.totalSupply
#@ performs: reallocate(?eth_amount?, to=msg.sender, acting_for=self)
# TODO: The following acting_for feels weird... (should be "from")
# FIXME: ?token_amount? == amount * balanceOf(self.token, self) / self.totalSupply
#@ performs: reallocate[token[self.token]](?token_amount?, to=msg.sender, acting_for=self)
#@ performs: destroy[UNI](amount)
@public
def removeLiquidity(amount: uint256, min_eth: uint256(wei), min_tokens: uint256, deadline: timestamp) -> EtherTokenPair:
    assert (amount > 0 and deadline > block.timestamp) and (min_eth > 0 and min_tokens > 0)
    total_liquidity: uint256 = self.totalSupply
    assert total_liquidity > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_amount: uint256(wei) = amount * self.balance / total_liquidity
    token_amount: uint256 = amount * token_reserve / total_liquidity
    assert eth_amount >= min_eth and token_amount >= min_tokens
    #@ reallocate(eth_amount, to=msg.sender, acting_for=self)
    self.balances[msg.sender] -= amount
    #@ destroy[UNI](amount)
    self.totalSupply = total_liquidity - amount
    send(msg.sender, eth_amount)
    assert_modifiable(self.token.transfer(msg.sender, token_amount))
    log.RemoveLiquidity(msg.sender, eth_amount, token_amount)
    log.Transfer(msg.sender, ZERO_ADDRESS, amount)
    return EtherTokenPair({_ether: eth_amount, _token: token_amount})

# @dev Pricing function for converting between ETH and Tokens.
# @param input_amount Amount of ETH or Tokens being sold.
# @param input_reserve Amount of ETH or Tokens (input type) in exchange reserves.
# @param output_reserve Amount of ETH or Tokens (output type) in exchange reserves.
# @return Amount of ETH or Tokens bought.
#@pure
@private
@constant
def getInputPrice(input_amount: uint256, input_reserve: uint256, output_reserve: uint256) -> uint256:
    assert input_reserve > 0 and output_reserve > 0
    input_amount_with_fee: uint256 = input_amount * 997
    numerator: uint256 = input_amount_with_fee * output_reserve
    denominator: uint256 = (input_reserve * 1000) + input_amount_with_fee
    return numerator / denominator

# @dev Pricing function for converting between ETH and Tokens.
# @param output_amount Amount of ETH or Tokens being bought.
# @param input_reserve Amount of ETH or Tokens (input type) in exchange reserves.
# @param output_reserve Amount of ETH or Tokens (output type) in exchange reserves.
# @return Amount of ETH or Tokens sold.
#@pure
@private
@constant
def getOutputPrice(output_amount: uint256, input_reserve: uint256, output_reserve: uint256) -> uint256:
    assert input_reserve > 0 and output_reserve > 0
    numerator: uint256 = input_reserve * output_amount * 1000
    denominator: uint256 = (output_reserve - output_amount) * 997
    return numerator / denominator + 1

# TODO: Is there something better than these preconditions?
#@ requires: allocated() == public_old(allocated())
#@ requires: allocated[UNI]() == public_old(allocated[UNI]())
#@ requires: forall({o: address, s: address}, offered[UNI <-> UNI](1, 0, o, s) == public_old(offered[UNI <-> UNI](1, 0, o, s)))
#@ requires: forall({a: address}, allocated[creator(UNI)](a) == 1)
#@ requires: forall({a: address}, trusted(a, by=self))
#@ requires: storage(self) == public_old(storage(self))
#@ performs: reallocate(eth_sold, to=self)
# TODO: How should private function calls be handled, if they contain resource modification?
# FIXME: ?tokens_bought? == self.getInputPrice(eth_sold, self.balance - eth_sold, balanceOf(self.token, self))
#@ performs: reallocate[token[self.token]](?tokens_bought?, to=recipient, acting_for=self)
@private
def ethToTokenInput(eth_sold: uint256(wei), min_tokens: uint256, deadline: timestamp, buyer: address, recipient: address) -> uint256:
    #@ reallocate(eth_sold, to=self)
    assert deadline >= block.timestamp and (eth_sold > 0 and min_tokens > 0)
    token_reserve: uint256 = self.token.balanceOf(self)
    tokens_bought: uint256 = self.getInputPrice(as_unitless_number(eth_sold), as_unitless_number(self.balance - eth_sold), token_reserve)
    assert tokens_bought >= min_tokens
    assert_modifiable(self.token.transfer(recipient, tokens_bought))
    log.TokenPurchase(buyer, eth_sold, tokens_bought)
    return tokens_bought

# @notice Convert ETH to Tokens.
# @dev User specifies exact input (msg.value).
# @dev User cannot specify minimum output or deadline.
#@ performs: reallocate(msg.value, to=self)
#@ performs: reallocate[token[self.token]](???, to=msg.sender, acting_for=self)
@public
@payable
def __default__():
    self.ethToTokenInput(msg.value, 1, block.timestamp, msg.sender, msg.sender)

# @notice Convert ETH to Tokens.
# @dev User specifies exact input (msg.value) and minimum output.
# @param min_tokens Minimum Tokens bought.
# @param deadline Time after which this transaction can no longer be executed.
# @return Amount of Tokens bought.
#@ performs: reallocate(msg.value, to=self)
#@ performs: reallocate[token[self.token]](???, to=msg.sender, acting_for=self)
@public
@payable
def ethToTokenSwapInput(min_tokens: uint256, deadline: timestamp) -> uint256:
    return self.ethToTokenInput(msg.value, min_tokens, deadline, msg.sender, msg.sender)

# @notice Convert ETH to Tokens and transfers Tokens to recipient.
# @dev User specifies exact input (msg.value) and minimum output
# @param min_tokens Minimum Tokens bought.
# @param deadline Time after which this transaction can no longer be executed.
# @param recipient The address that receives output Tokens.
# @return Amount of Tokens bought.
#@ performs: reallocate(msg.value, to=self)
#@ performs: reallocate[token[self.token]](???, to=recipient, acting_for=self)
@public
@payable
def ethToTokenTransferInput(min_tokens: uint256, deadline: timestamp, recipient: address) -> uint256:
    assert recipient != self and recipient != ZERO_ADDRESS
    return self.ethToTokenInput(msg.value, min_tokens, deadline, msg.sender, recipient)

#@ requires: allocated() == public_old(allocated())
#@ requires: allocated[UNI]() == public_old(allocated[UNI]())
#@ requires: forall({o: address, s: address}, offered[UNI <-> UNI](1, 0, o, s) == public_old(offered[UNI <-> UNI](1, 0, o, s)))
#@ requires: forall({a: address}, allocated[creator(UNI)](a) == 1)
#@ requires: forall({a: address}, trusted(a, by=self))
#@ requires: storage(self) == public_old(storage(self))
#@ performs: reallocate(max_eth, to=self)
# FIXME: ?eth_refund? == max(0, max_eth - self.getOutputPrice(tokens_bought, self.balance - max_eth, balanceOf(self.token, self)))
#@ performs: reallocate(?eth_refund?, to=buyer, acting_for=self)
#@ performs: reallocate[token[self.token]](tokens_bought, to=recipient, acting_for=self)
@private
def ethToTokenOutput(tokens_bought: uint256, max_eth: uint256(wei), deadline: timestamp, buyer: address, recipient: address) -> uint256(wei):
    #@ reallocate(max_eth, to=self)
    assert deadline >= block.timestamp and (tokens_bought > 0 and max_eth > 0)
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_sold: uint256 = self.getOutputPrice(tokens_bought, as_unitless_number(self.balance - max_eth), token_reserve)
    # Throws if eth_sold > max_eth
    eth_refund: uint256(wei) = max_eth - as_wei_value(eth_sold, 'wei')
    if eth_refund > 0:
        #@ reallocate(eth_refund, to=buyer, acting_for=self)
        send(buyer, eth_refund)
    assert_modifiable(self.token.transfer(recipient, tokens_bought))
    log.TokenPurchase(buyer, as_wei_value(eth_sold, 'wei'), tokens_bought)
    return as_wei_value(eth_sold, 'wei')

# @notice Convert ETH to Tokens.
# @dev User specifies maximum input (msg.value) and exact output.
# @param tokens_bought Amount of tokens bought.
# @param deadline Time after which this transaction can no longer be executed.
# @return Amount of ETH sold.
#@ performs: reallocate(msg.value, to=self)  # TODO: Get some ether... Reallocate to self <-> msg.sender
#@ performs: reallocate(???, to=msg.sender, acting_for=self)  # TODO: Refund some ether... Reallocate to self <-> msg.sender
#@ performs: reallocate[token[self.token]](tokens_bought, to=msg.sender, acting_for=self)
@public
@payable
def ethToTokenSwapOutput(tokens_bought: uint256, deadline: timestamp) -> uint256(wei):
    return self.ethToTokenOutput(tokens_bought, msg.value, deadline, msg.sender, msg.sender)

# @notice Convert ETH to Tokens and transfers Tokens to recipient.
# @dev User specifies maximum input (msg.value) and exact output.
# @param tokens_bought Amount of tokens bought.
# @param deadline Time after which this transaction can no longer be executed.
# @param recipient The address that receives output Tokens.
# @return Amount of ETH sold.
#@ performs: reallocate(msg.value, to=self)  # TODO: Get some ether... Reallocate to self <-> msg.sender
#@ performs: reallocate(???, to=msg.sender, acting_for=self)  # TODO: Refund some ether... Reallocate to self <-> msg.sender
#@ performs: reallocate[token[self.token]](tokens_bought, to=recipient, acting_for=self)
@public
@payable
def ethToTokenTransferOutput(tokens_bought: uint256, deadline: timestamp, recipient: address) -> uint256(wei):
    assert recipient != self and recipient != ZERO_ADDRESS
    return self.ethToTokenOutput(tokens_bought, msg.value, deadline, msg.sender, recipient)

#@ requires: allocated() == public_old(allocated())
#@ requires: allocated[UNI]() == public_old(allocated[UNI]())
#@ requires: forall({o: address, s: address}, offered[UNI <-> UNI](1, 0, o, s) == public_old(offered[UNI <-> UNI](1, 0, o, s)))
#@ requires: forall({a: address}, allocated[creator(UNI)](a) == 1)
#@ requires: forall({a: address}, trusted(a, by=self))
#@ requires: storage(self) == public_old(storage(self))
#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=buyer)  # TODO: It is a transferFrom... Can we write reallocate?
# FIXME: #@ performs: exchange[token[self.token] <-> token[self.token]](1, 0, buyer, self, times=tokens_sold)
# FIXME: ?eth_bought? == self.getInputPrice(tokens_sold, balanceOf(self.token, self), self.balance)
#@ performs: reallocate(?eth_bought?, to=recipient, acting_for=self)
@private
def tokenToEthInput(tokens_sold: uint256, min_eth: uint256(wei), deadline: timestamp, buyer: address, recipient: address) -> uint256(wei):
    assert deadline >= block.timestamp and (tokens_sold > 0 and min_eth > 0)
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_bought: uint256 = self.getInputPrice(tokens_sold, token_reserve, as_unitless_number(self.balance))
    wei_bought: uint256(wei) = as_wei_value(eth_bought, 'wei')
    assert wei_bought >= min_eth
    #@ reallocate(eth_bought, to=recipient, acting_for=self)
    send(recipient, wei_bought)
    assert_modifiable(self.token.transferFrom(buyer, self, tokens_sold))
    log.EthPurchase(buyer, tokens_sold, wei_bought)
    return wei_bought

# @notice Convert Tokens to ETH.
# @dev User specifies exact input and minimum output.
# @param tokens_sold Amount of Tokens sold.
# @param min_eth Minimum ETH purchased.
# @param deadline Time after which this transaction can no longer be executed.
# @return Amount of ETH bought.
#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate(???, to=msg.sender, acting_for=self)
@public
def tokenToEthSwapInput(tokens_sold: uint256, min_eth: uint256(wei), deadline: timestamp) -> uint256(wei):
    return self.tokenToEthInput(tokens_sold, min_eth, deadline, msg.sender, msg.sender)

# @notice Convert Tokens to ETH and transfers ETH to recipient.
# @dev User specifies exact input and minimum output.
# @param tokens_sold Amount of Tokens sold.
# @param min_eth Minimum ETH purchased.
# @param deadline Time after which this transaction can no longer be executed.
# @param recipient The address that receives output ETH.
# @return Amount of ETH bought.
#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate(???, to=recipient, acting_for=self)
@public
def tokenToEthTransferInput(tokens_sold: uint256, min_eth: uint256(wei), deadline: timestamp, recipient: address) -> uint256(wei):
    assert recipient != self and recipient != ZERO_ADDRESS
    return self.tokenToEthInput(tokens_sold, min_eth, deadline, msg.sender, recipient)

#@ requires: allocated() == public_old(allocated())
#@ requires: allocated[UNI]() == public_old(allocated[UNI]())
#@ requires: forall({o: address, s: address}, offered[UNI <-> UNI](1, 0, o, s) == public_old(offered[UNI <-> UNI](1, 0, o, s)))
#@ requires: forall({a: address}, allocated[creator(UNI)](a) == 1)
#@ requires: forall({a: address}, trusted(a, by=self))
#@ requires: storage(self) == public_old(storage(self))
# FIXME: ?tokens_sold? == self.getOutputPrice(eth_bought, balanceOf(self.token, self), self.balance)
#@ performs: reallocate[token[self.token]](?tokens_sold?, to=self, acting_for=buyer)  # TODO: It is a transferFrom... Can we write reallocate?
# FIXME: #@ performs: exchange[token[self.token] <-> token[self.token]](1, 0, buyer, self, times=?tokens_sold?)
#@ performs: reallocate(eth_bought, to=recipient, acting_for=self)
@private
def tokenToEthOutput(eth_bought: uint256(wei), max_tokens: uint256, deadline: timestamp, buyer: address, recipient: address) -> uint256:
    assert deadline >= block.timestamp and eth_bought > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    tokens_sold: uint256 = self.getOutputPrice(as_unitless_number(eth_bought), token_reserve, as_unitless_number(self.balance))
    # tokens sold is always > 0
    assert max_tokens >= tokens_sold
    #@ reallocate(eth_bought, to=recipient, acting_for=self)
    send(recipient, eth_bought)
    assert_modifiable(self.token.transferFrom(buyer, self, tokens_sold))
    log.EthPurchase(buyer, tokens_sold, eth_bought)
    return tokens_sold

# @notice Convert Tokens to ETH.
# @dev User specifies maximum input and exact output.
# @param eth_bought Amount of ETH purchased.
# @param max_tokens Maximum Tokens sold.
# @param deadline Time after which this transaction can no longer be executed.
# @return Amount of Tokens sold.
#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate(eth_bought, to=msg.sender, acting_for=self)
@public
def tokenToEthSwapOutput(eth_bought: uint256(wei), max_tokens: uint256, deadline: timestamp) -> uint256:
    return self.tokenToEthOutput(eth_bought, max_tokens, deadline, msg.sender, msg.sender)

# @notice Convert Tokens to ETH and transfers ETH to recipient.
# @dev User specifies maximum input and exact output.
# @param eth_bought Amount of ETH purchased.
# @param max_tokens Maximum Tokens sold.
# @param deadline Time after which this transaction can no longer be executed.
# @param recipient The address that receives output ETH.
# @return Amount of Tokens sold.
#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate(eth_bought, to=recipient, acting_for=self)
@public
def tokenToEthTransferOutput(eth_bought: uint256(wei), max_tokens: uint256, deadline: timestamp, recipient: address) -> uint256:
    assert recipient != self and recipient != ZERO_ADDRESS
    return self.tokenToEthOutput(eth_bought, max_tokens, deadline, msg.sender, recipient)

#@ requires: allocated() == public_old(allocated())
#@ requires: allocated[UNI]() == public_old(allocated[UNI]())
#@ requires: forall({o: address, s: address}, offered[UNI <-> UNI](1, 0, o, s) == public_old(offered[UNI <-> UNI](1, 0, o, s)))
#@ requires: forall({a: address}, allocated[creator(UNI)](a) == 1)
#@ requires: forall({a: address}, trusted(a, by=self))
#@ requires: storage(self) == public_old(storage(self))
#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=buyer)  # TODO: It is a transferFrom... Can we write reallocate?
# FIXME: #@ performs: exchange[token[self.token] <-> token[self.token]](1, 0, buyer, self, times=tokens_sold)
# FIXME: ?eth_bought? == self.getInputPrice(tokens_sold, balanceOf(self.token, self), self.balance)
#@ performs: reallocate(?eth_bought?, to=exchange_addr, acting_for=self)
# TODO: Only works if we believe that "self.token.transferFrom" does not change the price
#@ performs: reallocate[token[token(exchange_addr)]](getEthToTokenInputPrice(exchange_addr, ?eth_bought?), to=recipient, acting_for=exchange_addr)  # TODO: Is this what we want?
@private
def tokenToTokenInput(tokens_sold: uint256, min_tokens_bought: uint256, min_eth_bought: uint256(wei), deadline: timestamp, buyer: address, recipient: address, exchange_addr: address) -> uint256:
    assert (deadline >= block.timestamp and tokens_sold > 0) and (min_tokens_bought > 0 and min_eth_bought > 0)
    assert exchange_addr != self and exchange_addr != ZERO_ADDRESS
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_bought: uint256 = self.getInputPrice(tokens_sold, token_reserve, as_unitless_number(self.balance))
    wei_bought: uint256(wei) = as_wei_value(eth_bought, 'wei')
    assert wei_bought >= min_eth_bought
    assert_modifiable(self.token.transferFrom(buyer, self, tokens_sold))
    #@ reallocate(eth_bought, to=exchange_addr, acting_for=self)
    tokens_bought: uint256 = Exchange(exchange_addr).ethToTokenTransferInput(min_tokens_bought, deadline, recipient, value=wei_bought)
    log.EthPurchase(buyer, tokens_sold, wei_bought)
    return tokens_bought

# @notice Convert Tokens (self.token) to Tokens (token_addr).
# @dev User specifies exact input and minimum output.
# @param tokens_sold Amount of Tokens sold.
# @param min_tokens_bought Minimum Tokens (token_addr) purchased.
# @param min_eth_bought Minimum ETH purchased as intermediary.
# @param deadline Time after which this transaction can no longer be executed.
# @param token_addr The address of the token being purchased.
# @return Amount of Tokens (token_addr) bought.
#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate(???, to=getExchange(self.factory, token_addr), acting_for=self)
#@ performs: reallocate[token[token(getExchange(self.factory, token_addr))]](getEthToTokenInputPrice(getExchange(self.factory, token_addr), self.getInputPrice(tokens_sold, balanceOf(self.token, self), self.balance)), to=msg.sender, acting_for=getExchange(self.factory, token_addr))  # TODO: Is this what we want?
@public
def tokenToTokenSwapInput(tokens_sold: uint256, min_tokens_bought: uint256, min_eth_bought: uint256(wei), deadline: timestamp, token_addr: address) -> uint256:
    exchange_addr: address = self.factory.getExchange(token_addr)
    return self.tokenToTokenInput(tokens_sold, min_tokens_bought, min_eth_bought, deadline, msg.sender, msg.sender, exchange_addr)

# @notice Convert Tokens (self.token) to Tokens (token_addr) and transfers
#         Tokens (token_addr) to recipient.
# @dev User specifies exact input and minimum output.
# @param tokens_sold Amount of Tokens sold.
# @param min_tokens_bought Minimum Tokens (token_addr) purchased.
# @param min_eth_bought Minimum ETH purchased as intermediary.
# @param deadline Time after which this transaction can no longer be executed.
# @param recipient The address that receives output ETH.
# @param token_addr The address of the token being purchased.
# @return Amount of Tokens (token_addr) bought.
#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate(???, to=getExchange(self.factory, token_addr), acting_for=self)
#@ performs: reallocate[token[token(getExchange(self.factory, token_addr))]](getEthToTokenInputPrice(getExchange(self.factory, token_addr), ???), to=recipient, acting_for=getExchange(self.factory, token_addr))
@public
def tokenToTokenTransferInput(tokens_sold: uint256, min_tokens_bought: uint256, min_eth_bought: uint256(wei), deadline: timestamp, recipient: address, token_addr: address) -> uint256:
    exchange_addr: address = self.factory.getExchange(token_addr)
    return self.tokenToTokenInput(tokens_sold, min_tokens_bought, min_eth_bought, deadline, msg.sender, recipient, exchange_addr)

#@ requires: allocated() == public_old(allocated())
#@ requires: allocated[UNI]() == public_old(allocated[UNI]())
#@ requires: forall({o: address, s: address}, offered[UNI <-> UNI](1, 0, o, s) == public_old(offered[UNI <-> UNI](1, 0, o, s)))
#@ requires: forall({a: address}, allocated[creator(UNI)](a) == 1)
#@ requires: forall({a: address}, trusted(a, by=self))
#@ requires: storage(self) == public_old(storage(self))
# FIXME: ?token_sold? == self.getOutputPrice(getEthToTokenOutputPrice(exchange_addr, tokens_bought), balanceOf(self.token, self), self.balance)
#@ performs: reallocate[token[self.token]](?token_sold?, to=self, acting_for=buyer)  # TODO: It is a transferFrom... Can we write reallocate?
# FIXME: #@ performs: exchange[token[self.token] <-> token[self.token]](1, 0, buyer, self, times=?tokens_sold?)
#@ performs: reallocate(getEthToTokenOutputPrice(exchange_addr, tokens_bought), to=exchange_addr, acting_for=self)
# TODO: Only works if we believe that "self.token.transferFrom" does not change the price
#@ performs: reallocate[token[token(exchange_addr)]](tokens_bought, to=recipient, acting_for=exchange_addr)
@private
def tokenToTokenOutput(tokens_bought: uint256, max_tokens_sold: uint256, max_eth_sold: uint256(wei), deadline: timestamp, buyer: address, recipient: address, exchange_addr: address) -> uint256:
    assert deadline >= block.timestamp and (tokens_bought > 0 and max_eth_sold > 0)
    assert exchange_addr != self and exchange_addr != ZERO_ADDRESS
    eth_bought: uint256(wei) = Exchange(exchange_addr).getEthToTokenOutputPrice(tokens_bought)
    token_reserve: uint256 = self.token.balanceOf(self)
    tokens_sold: uint256 = self.getOutputPrice(as_unitless_number(eth_bought), token_reserve, as_unitless_number(self.balance))
    # tokens sold is always > 0
    assert max_tokens_sold >= tokens_sold and max_eth_sold >= eth_bought
    assert_modifiable(self.token.transferFrom(buyer, self, tokens_sold))
    #@ reallocate(eth_bought, to=exchange_addr, acting_for=self)
    eth_sold: uint256(wei) = Exchange(exchange_addr).ethToTokenTransferOutput(tokens_bought, deadline, recipient, value=eth_bought)
    log.EthPurchase(buyer, tokens_sold, eth_bought)
    return tokens_sold

# @notice Convert Tokens (self.token) to Tokens (token_addr).
# @dev User specifies maximum input and exact output.
# @param tokens_bought Amount of Tokens (token_addr) bought.
# @param max_tokens_sold Maximum Tokens (self.token) sold.
# @param max_eth_sold Maximum ETH purchased as intermediary.
# @param deadline Time after which this transaction can no longer be executed.
# @param token_addr The address of the token being purchased.
# @return Amount of Tokens (self.token) sold.
#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate(getEthToTokenOutputPrice(getExchange(self.factory, token_addr), tokens_bought), to=getExchange(self.factory, token_addr), acting_for=self)
#@ performs: reallocate[token[token(getExchange(self.factory, token_addr))]](tokens_bought, to=msg.sender, acting_for=getExchange(self.factory, token_addr))
@public
def tokenToTokenSwapOutput(tokens_bought: uint256, max_tokens_sold: uint256, max_eth_sold: uint256(wei), deadline: timestamp, token_addr: address) -> uint256:
    exchange_addr: address = self.factory.getExchange(token_addr)
    return self.tokenToTokenOutput(tokens_bought, max_tokens_sold, max_eth_sold, deadline, msg.sender, msg.sender, exchange_addr)

# @notice Convert Tokens (self.token) to Tokens (token_addr) and transfers
#         Tokens (token_addr) to recipient.
# @dev User specifies maximum input and exact output.
# @param tokens_bought Amount of Tokens (token_addr) bought.
# @param max_tokens_sold Maximum Tokens (self.token) sold.
# @param max_eth_sold Maximum ETH purchased as intermediary.
# @param deadline Time after which this transaction can no longer be executed.
# @param recipient The address that receives output ETH.
# @param token_addr The address of the token being purchased.
# @return Amount of Tokens (self.token) sold.
#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate(getEthToTokenOutputPrice(getExchange(self.factory, token_addr), tokens_bought), to=getExchange(self.factory, token_addr), acting_for=self)
#@ performs: reallocate[token[token(getExchange(self.factory, token_addr))]](tokens_bought, to=recipient, acting_for=getExchange(self.factory, token_addr))
@public
def tokenToTokenTransferOutput(tokens_bought: uint256, max_tokens_sold: uint256, max_eth_sold: uint256(wei), deadline: timestamp, recipient: address, token_addr: address) -> uint256:
    exchange_addr: address = self.factory.getExchange(token_addr)
    return self.tokenToTokenOutput(tokens_bought, max_tokens_sold, max_eth_sold, deadline, msg.sender, recipient, exchange_addr)

# @notice Convert Tokens (self.token) to Tokens (exchange_addr.token).
# @dev Allows trades through contracts that were not deployed from the same factory.
# @dev User specifies exact input and minimum output.
# @param tokens_sold Amount of Tokens sold.
# @param min_tokens_bought Minimum Tokens (token_addr) purchased.
# @param min_eth_bought Minimum ETH purchased as intermediary.
# @param deadline Time after which this transaction can no longer be executed.
# @param exchange_addr The address of the exchange for the token being purchased.
# @return Amount of Tokens (exchange_addr.token) bought.
#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate(???, to=exchange_addr, acting_for=self)
#@ performs: reallocate[token[token(exchange_addr)]](getEthToTokenInputPrice(exchange_addr, ???), to=msg.sender, acting_for=exchange_addr)
@public
def tokenToExchangeSwapInput(tokens_sold: uint256, min_tokens_bought: uint256, min_eth_bought: uint256(wei), deadline: timestamp, exchange_addr: address) -> uint256:
    return self.tokenToTokenInput(tokens_sold, min_tokens_bought, min_eth_bought, deadline, msg.sender, msg.sender, exchange_addr)

# @notice Convert Tokens (self.token) to Tokens (exchange_addr.token) and transfers
#         Tokens (exchange_addr.token) to recipient.
# @dev Allows trades through contracts that were not deployed from the same factory.
# @dev User specifies exact input and minimum output.
# @param tokens_sold Amount of Tokens sold.
# @param min_tokens_bought Minimum Tokens (token_addr) purchased.
# @param min_eth_bought Minimum ETH purchased as intermediary.
# @param deadline Time after which this transaction can no longer be executed.
# @param recipient The address that receives output ETH.
# @param exchange_addr The address of the exchange for the token being purchased.
# @return Amount of Tokens (exchange_addr.token) bought.
#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate(???, to=exchange_addr, acting_for=self)
#@ performs: reallocate[token[token(exchange_addr)]](getEthToTokenInputPrice(exchange_addr, ???), to=recipient, acting_for=exchange_addr)
@public
def tokenToExchangeTransferInput(tokens_sold: uint256, min_tokens_bought: uint256, min_eth_bought: uint256(wei), deadline: timestamp, recipient: address, exchange_addr: address) -> uint256:
    assert recipient != self
    return self.tokenToTokenInput(tokens_sold, min_tokens_bought, min_eth_bought, deadline, msg.sender, recipient, exchange_addr)

# @notice Convert Tokens (self.token) to Tokens (exchange_addr.token).
# @dev Allows trades through contracts that were not deployed from the same factory.
# @dev User specifies maximum input and exact output.
# @param tokens_bought Amount of Tokens (token_addr) bought.
# @param max_tokens_sold Maximum Tokens (self.token) sold.
# @param max_eth_sold Maximum ETH purchased as intermediary.
# @param deadline Time after which this transaction can no longer be executed.
# @param exchange_addr The address of the exchange for the token being purchased.
# @return Amount of Tokens (self.token) sold.
#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate(getEthToTokenOutputPrice(exchange_addr, tokens_bought), to=exchange_addr, acting_for=self)
#@ performs: reallocate[token[token(exchange_addr)]](tokens_bought, to=msg.sender, acting_for=exchange_addr)
@public
def tokenToExchangeSwapOutput(tokens_bought: uint256, max_tokens_sold: uint256, max_eth_sold: uint256(wei), deadline: timestamp, exchange_addr: address) -> uint256:
    return self.tokenToTokenOutput(tokens_bought, max_tokens_sold, max_eth_sold, deadline, msg.sender, msg.sender, exchange_addr)

# @notice Convert Tokens (self.token) to Tokens (exchange_addr.token) and transfers
#         Tokens (exchange_addr.token) to recipient.
# @dev Allows trades through contracts that were not deployed from the same factory.
# @dev User specifies maximum input and exact output.
# @param tokens_bought Amount of Tokens (token_addr) bought.
# @param max_tokens_sold Maximum Tokens (self.token) sold.
# @param max_eth_sold Maximum ETH purchased as intermediary.
# @param deadline Time after which this transaction can no longer be executed.
# @param recipient The address that receives output ETH.
# @param token_addr The address of the token being purchased.
# @return Amount of Tokens (self.token) sold.
#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate(getEthToTokenOutputPrice(exchange_addr, tokens_bought), to=exchange_addr, acting_for=self)
#@ performs: reallocate[token[token(exchange_addr)]](tokens_bought, to=recipient, acting_for=exchange_addr)
@public
def tokenToExchangeTransferOutput(tokens_bought: uint256, max_tokens_sold: uint256, max_eth_sold: uint256(wei), deadline: timestamp, recipient: address, exchange_addr: address) -> uint256:
    assert recipient != self
    return self.tokenToTokenOutput(tokens_bought, max_tokens_sold, max_eth_sold, deadline, msg.sender, recipient, exchange_addr)

# @notice Public price function for ETH to Token trades with an exact input.
# @param eth_sold Amount of ETH sold.
# @return Amount of Tokens that can be bought with input ETH.
#@ ensures: success() ==> result() == getEthToTokenInputPrice(self, eth_sold)
@public
@constant
def getEthToTokenInputPrice(eth_sold: uint256(wei)) -> uint256:
    assert eth_sold > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    return self.getInputPrice(as_unitless_number(eth_sold), as_unitless_number(self.balance), token_reserve)

# @notice Public price function for ETH to Token trades with an exact output.
# @param tokens_bought Amount of Tokens bought.
# @return Amount of ETH needed to buy output Tokens.
#@ ensures: success() ==> result() == getEthToTokenOutputPrice(self, tokens_bought)
@public
@constant
def getEthToTokenOutputPrice(tokens_bought: uint256) -> uint256(wei):
    assert tokens_bought > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_sold: uint256 = self.getOutputPrice(tokens_bought, as_unitless_number(self.balance), token_reserve)
    return as_wei_value(eth_sold, 'wei')

# @notice Public price function for Token to ETH trades with an exact input.
# @param tokens_sold Amount of Tokens sold.
# @return Amount of ETH that can be bought with input Tokens.
@public
@constant
def getTokenToEthInputPrice(tokens_sold: uint256) -> uint256(wei):
    assert tokens_sold > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_bought: uint256 = self.getInputPrice(tokens_sold, token_reserve, as_unitless_number(self.balance))
    return as_wei_value(eth_bought, 'wei')

# @notice Public price function for Token to ETH trades with an exact output.
# @param eth_bought Amount of output ETH.
# @return Amount of Tokens needed to buy output ETH.
@public
@constant
def getTokenToEthOutputPrice(eth_bought: uint256(wei)) -> uint256:
    assert eth_bought > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    return self.getOutputPrice(as_unitless_number(eth_bought), token_reserve, as_unitless_number(self.balance))

# @return Address of Token that is sold on this exchange.
#@ ensures: success() ==> result() == token(self)
@public
@constant
def tokenAddress() -> address:
    return self.token

# @return Address of factory that created this exchange.
@public
@constant
def factoryAddress() -> address(Factory):
    return self.factory

# ERC20 compatibility for exchange liquidity modified from
# https://github.com/ethereum/vyper/blob/master/examples/tokens/ERC20.vy
#@ ensures: success() ==> result() == allocated[UNI](_owner)
@public
@constant
def balanceOf(_owner: address) -> uint256:
    return self.balances[_owner]

#@ performs: reallocate[UNI](_value, to=_to)
#@ ensures: success() ==> result()
@public
def transfer(_to: address, _value: uint256) -> bool:
    self.balances[msg.sender] -= _value
    self.balances[_to] += _value
    log.Transfer(msg.sender, _to, _value)
    return True

#@ performs: exchange[UNI <-> UNI](1, 0, _from, msg.sender, times=_value)  # Exchanges deal with allowance
#@ performs: reallocate[UNI](_value, to=_to)
#@ ensures: success() ==> result()
@public
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    self.balances[_from] -= _value
    self.balances[_to] += _value
    self.allowances[_from][msg.sender] -= _value
    log.Transfer(_from, _to, _value)
    return True

#@ performs: revoke[UNI <-> UNI](1, 0, to=_spender)
#@ performs: offer[UNI <-> UNI](1, 0, to=_spender, times=_value)
#@ ensures: success() ==> result()
@public
def approve(_spender: address, _value: uint256) -> bool:
    self.allowances[msg.sender][_spender] = _value
    log.Approval(msg.sender, _spender, _value)
    return True

#@ ensures: success() ==> result() == offered[UNI <-> UNI](1, 0, _owner, _spender)
@public
@constant
def allowance(_owner: address, _spender: address) -> uint256:
    return self.allowances[_owner][_spender]
