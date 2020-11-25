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

#@ meta resource: UNI() -> [(self.balance / self.totalSupply if self.totalSupply > 0 else 1) * WEI,
                         #@ (balanceOf(self.token, self) / self.totalSupply if self.totalSupply > 0 else 0) * token[self.token]],
                         #@ self.balance * balanceOf(self.token, self)

#@ meta resource wei() -> [1 * WEI], 1

#@ invariant: old(self.factory) != ZERO_ADDRESS ==> self.factory == old(self.factory)
#@ invariant: old(self.factory) != ZERO_ADDRESS ==> self.token == old(self.token)

#@ invariant: sum(balances(self)) == self.totalSupply
#@ invariant: allocated[UNI]() == balances(self)

#@ invariant: forall({o: address, s: address}, self.allowances[o][s] == offered[UNI <-> UNI](1, 0, o, s))


@public
def setup(token_addr: address):
    assert (self.factory == ZERO_ADDRESS and self.token == ZERO_ADDRESS) and token_addr != ZERO_ADDRESS
    self.factory = Factory(msg.sender)
    self.token = ERC20(token_addr)
    self.name = 0x556e697377617020563100000000000000000000000000000000000000000000
    self.symbol = 0x554e492d56310000000000000000000000000000000000000000000000000000
    self.decimals = 18

#@ performs: allocate_untracked[UNI](msg.sender)
# FIXME: ?liquidity_minted? == msg.value * self.totalSupply / self.balance
#@ performs: payable[UNI](msg.value if self.totalSupply == 0 else ?liquidity_minted?)
@public
@payable
def addLiquidity(min_liquidity: uint256, max_tokens: uint256, deadline: timestamp) -> uint256:
    assert deadline > block.timestamp and (max_tokens > 0 and msg.value > 0)
    total_liquidity: uint256 = self.totalSupply
    #@ allocate_untracked_wei(self)
    if total_liquidity > 0:
        assert min_liquidity > 0
        eth_reserve: uint256(wei) = self.balance - msg.value
        token_reserve: uint256 = self.token.balanceOf(self)
        token_amount: uint256 = msg.value * token_reserve / eth_reserve + 1
        liquidity_minted: uint256 = msg.value * total_liquidity / eth_reserve
        assert max_tokens >= token_amount and liquidity_minted >= min_liquidity
        self.balances[msg.sender] += liquidity_minted
        self.totalSupply = total_liquidity + liquidity_minted
        assert_modifiable(self.token.transferFrom(msg.sender, self, token_amount))
        log.AddLiquidity(msg.sender, msg.value, token_amount)
        log.Transfer(ZERO_ADDRESS, msg.sender, liquidity_minted)
        return liquidity_minted
    else:
        assert (self.factory != ZERO_ADDRESS and self.token != ZERO_ADDRESS) and msg.value >= 1000000000
        assert self.factory.getExchange(self.token) == self
        token_amount: uint256 = max_tokens
        initial_liquidity: uint256 = as_unitless_number(self.balance)
        self.totalSupply = initial_liquidity
        self.balances[msg.sender] = initial_liquidity
        assert_modifiable(self.token.transferFrom(msg.sender, self, token_amount))
        log.AddLiquidity(msg.sender, msg.value, token_amount)
        log.Transfer(ZERO_ADDRESS, msg.sender, initial_liquidity)
        return initial_liquidity

#@ performs: payout[UNI](amount)
@public
def removeLiquidity(amount: uint256, min_eth: uint256(wei), min_tokens: uint256, deadline: timestamp) -> EtherTokenPair:
    assert (amount > 0 and deadline > block.timestamp) and (min_eth > 0 and min_tokens > 0)
    total_liquidity: uint256 = self.totalSupply
    assert total_liquidity > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_amount: uint256(wei) = amount * self.balance / total_liquidity
    token_amount: uint256 = amount * token_reserve / total_liquidity
    assert eth_amount >= min_eth and token_amount >= min_tokens
    self.balances[msg.sender] -= amount
    self.totalSupply = total_liquidity - amount
    send(msg.sender, eth_amount)
    assert_modifiable(self.token.transfer(msg.sender, token_amount))
    log.RemoveLiquidity(msg.sender, eth_amount, token_amount)
    log.Transfer(msg.sender, ZERO_ADDRESS, amount)
    return EtherTokenPair({_ether: eth_amount, _token: token_amount})

#@pure
@private
@constant
def getInputPrice(input_amount: uint256, input_reserve: uint256, output_reserve: uint256) -> uint256:
    assert input_reserve > 0 and output_reserve > 0
    input_amount_with_fee: uint256 = input_amount * 997
    numerator: uint256 = input_amount_with_fee * output_reserve
    denominator: uint256 = (input_reserve * 1000) + input_amount_with_fee
    return numerator / denominator

#@pure
@private
@constant
def getOutputPrice(output_amount: uint256, input_reserve: uint256, output_reserve: uint256) -> uint256:
    assert input_reserve > 0 and output_reserve > 0
    numerator: uint256 = input_reserve * output_amount * 1000
    denominator: uint256 = (output_reserve - output_amount) * 997
    return numerator / denominator + 1

# FIXME: ?tokens_bought? == self.getInputPrice(eth_sold, self.balance - eth_sold, balanceOf(self.token, self))
#@ performs: reallocate[token[self.token]](?tokens_bought?, to=recipient, acting_for=self)
@private
def ethToTokenInput(eth_sold: uint256(wei), min_tokens: uint256, deadline: timestamp, buyer: address, recipient: address) -> uint256:
    assert deadline >= block.timestamp and (eth_sold > 0 and min_tokens > 0)
    token_reserve: uint256 = self.token.balanceOf(self)
    tokens_bought: uint256 = self.getInputPrice(as_unitless_number(eth_sold), as_unitless_number(self.balance - eth_sold), token_reserve)
    assert tokens_bought >= min_tokens
    assert_modifiable(self.token.transfer(recipient, tokens_bought))
    log.TokenPurchase(buyer, eth_sold, tokens_bought)
    return tokens_bought

#@ performs: reallocate[token[self.token]](???, to=msg.sender, acting_for=self)
@public
@payable
def __default__():
    self.ethToTokenInput(msg.value, 1, block.timestamp, msg.sender, msg.sender)

#@ performs: reallocate[token[self.token]](???, to=msg.sender, acting_for=self)
@public
@payable
def ethToTokenSwapInput(min_tokens: uint256, deadline: timestamp) -> uint256:
    return self.ethToTokenInput(msg.value, min_tokens, deadline, msg.sender, msg.sender)

#@ performs: reallocate[token[self.token]](???, to=recipient, acting_for=self)
@public
@payable
def ethToTokenTransferInput(min_tokens: uint256, deadline: timestamp, recipient: address) -> uint256:
    assert recipient != self and recipient != ZERO_ADDRESS
    return self.ethToTokenInput(msg.value, min_tokens, deadline, msg.sender, recipient)

# FIXME: ?eth_refund? == max(0, max_eth - self.getOutputPrice(tokens_bought, self.balance - max_eth, balanceOf(self.token, self)))
#@ performs: reallocate[WEI](?eth_refund?, to=buyer, acting_for=self)
#@ performs: reallocate[token[self.token]](tokens_bought, to=recipient, acting_for=self)
@private
def ethToTokenOutput(tokens_bought: uint256, max_eth: uint256(wei), deadline: timestamp, buyer: address, recipient: address) -> uint256(wei):
    assert deadline >= block.timestamp and (tokens_bought > 0 and max_eth > 0)
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_sold: uint256 = self.getOutputPrice(tokens_bought, as_unitless_number(self.balance - max_eth), token_reserve)
    # Throws if eth_sold > max_eth
    eth_refund: uint256(wei) = max_eth - as_wei_value(eth_sold, 'wei')
    if eth_refund > 0:
        send(buyer, eth_refund)
    assert_modifiable(self.token.transfer(recipient, tokens_bought))
    log.TokenPurchase(buyer, as_wei_value(eth_sold, 'wei'), tokens_bought)
    return as_wei_value(eth_sold, 'wei')

#@ performs: reallocate[WEI](???, to=msg.sender, acting_for=self)
#@ performs: reallocate[token[self.token]](tokens_bought, to=msg.sender, acting_for=self)
@public
@payable
def ethToTokenSwapOutput(tokens_bought: uint256, deadline: timestamp) -> uint256(wei):
    return self.ethToTokenOutput(tokens_bought, msg.value, deadline, msg.sender, msg.sender)

#@ performs: reallocate[WEI](???, to=msg.sender, acting_for=self)
#@ performs: reallocate[token[self.token]](tokens_bought, to=recipient, acting_for=self)
@public
@payable
def ethToTokenTransferOutput(tokens_bought: uint256, deadline: timestamp, recipient: address) -> uint256(wei):
    assert recipient != self and recipient != ZERO_ADDRESS
    return self.ethToTokenOutput(tokens_bought, msg.value, deadline, msg.sender, recipient)

#@ performs: exchange[token[self.token] <-> token[self.token]](1, 0, buyer, self, times=tokens_sold)
# FIXME: ?eth_bought? == self.getInputPrice(tokens_sold, balanceOf(self.token, self), self.balance)
#@ performs: reallocate[WEI](?eth_bought?, to=recipient, acting_for=self)
@private
def tokenToEthInput(tokens_sold: uint256, min_eth: uint256(wei), deadline: timestamp, buyer: address, recipient: address) -> uint256(wei):
    assert deadline >= block.timestamp and (tokens_sold > 0 and min_eth > 0)
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_bought: uint256 = self.getInputPrice(tokens_sold, token_reserve, as_unitless_number(self.balance))
    wei_bought: uint256(wei) = as_wei_value(eth_bought, 'wei')
    assert wei_bought >= min_eth
    send(recipient, wei_bought)
    assert_modifiable(self.token.transferFrom(buyer, self, tokens_sold))
    log.EthPurchase(buyer, tokens_sold, wei_bought)
    return wei_bought

#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate[WEI](???, to=msg.sender, acting_for=self)
@public
def tokenToEthSwapInput(tokens_sold: uint256, min_eth: uint256(wei), deadline: timestamp) -> uint256(wei):
    return self.tokenToEthInput(tokens_sold, min_eth, deadline, msg.sender, msg.sender)

#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate[WEI](???, to=recipient, acting_for=self)
@public
def tokenToEthTransferInput(tokens_sold: uint256, min_eth: uint256(wei), deadline: timestamp, recipient: address) -> uint256(wei):
    assert recipient != self and recipient != ZERO_ADDRESS
    return self.tokenToEthInput(tokens_sold, min_eth, deadline, msg.sender, recipient)

# FIXME: ?tokens_sold? == self.getOutputPrice(eth_bought, balanceOf(self.token, self), self.balance)
#@ performs: exchange[token[self.token] <-> token[self.token]](1, 0, buyer, self, times=?tokens_sold?)
#@ performs: reallocate[WEI](eth_bought, to=recipient, acting_for=self)
@private
def tokenToEthOutput(eth_bought: uint256(wei), max_tokens: uint256, deadline: timestamp, buyer: address, recipient: address) -> uint256:
    assert deadline >= block.timestamp and eth_bought > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    tokens_sold: uint256 = self.getOutputPrice(as_unitless_number(eth_bought), token_reserve, as_unitless_number(self.balance))
    # tokens sold is always > 0
    assert max_tokens >= tokens_sold
    send(recipient, eth_bought)
    assert_modifiable(self.token.transferFrom(buyer, self, tokens_sold))
    log.EthPurchase(buyer, tokens_sold, eth_bought)
    return tokens_sold

#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate[WEI](eth_bought, to=msg.sender, acting_for=self)
@public
def tokenToEthSwapOutput(eth_bought: uint256(wei), max_tokens: uint256, deadline: timestamp) -> uint256:
    return self.tokenToEthOutput(eth_bought, max_tokens, deadline, msg.sender, msg.sender)

#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate[WEI](eth_bought, to=recipient, acting_for=self)
@public
def tokenToEthTransferOutput(eth_bought: uint256(wei), max_tokens: uint256, deadline: timestamp, recipient: address) -> uint256:
    assert recipient != self and recipient != ZERO_ADDRESS
    return self.tokenToEthOutput(eth_bought, max_tokens, deadline, msg.sender, recipient)

#@ performs: exchange[token[self.token] <-> token[self.token]](1, 0, buyer, self, times=tokens_sold)
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
    tokens_bought: uint256 = Exchange(exchange_addr).ethToTokenTransferInput(min_tokens_bought, deadline, recipient, value=wei_bought)
    log.EthPurchase(buyer, tokens_sold, wei_bought)
    return tokens_bought

#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate[token[token(getExchange(self.factory, token_addr))]](getEthToTokenInputPrice(getExchange(self.factory, token_addr), self.getInputPrice(tokens_sold, balanceOf(self.token, self), self.balance)), to=msg.sender, acting_for=getExchange(self.factory, token_addr))  # TODO: Is this what we want?
@public
def tokenToTokenSwapInput(tokens_sold: uint256, min_tokens_bought: uint256, min_eth_bought: uint256(wei), deadline: timestamp, token_addr: address) -> uint256:
    exchange_addr: address = self.factory.getExchange(token_addr)
    return self.tokenToTokenInput(tokens_sold, min_tokens_bought, min_eth_bought, deadline, msg.sender, msg.sender, exchange_addr)

#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate[token[token(getExchange(self.factory, token_addr))]](getEthToTokenInputPrice(getExchange(self.factory, token_addr), ???), to=recipient, acting_for=getExchange(self.factory, token_addr))
@public
def tokenToTokenTransferInput(tokens_sold: uint256, min_tokens_bought: uint256, min_eth_bought: uint256(wei), deadline: timestamp, recipient: address, token_addr: address) -> uint256:
    exchange_addr: address = self.factory.getExchange(token_addr)
    return self.tokenToTokenInput(tokens_sold, min_tokens_bought, min_eth_bought, deadline, msg.sender, recipient, exchange_addr)

# FIXME: ?token_sold? == self.getOutputPrice(getEthToTokenOutputPrice(exchange_addr, tokens_bought), balanceOf(self.token, self), self.balance)
#@ performs: exchange[token[self.token] <-> token[self.token]](1, 0, buyer, self, times=?tokens_sold?)
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
    eth_sold: uint256(wei) = Exchange(exchange_addr).ethToTokenTransferOutput(tokens_bought, deadline, recipient, value=eth_bought)
    log.EthPurchase(buyer, tokens_sold, eth_bought)
    return tokens_sold

#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate[token[token(getExchange(self.factory, token_addr))]](tokens_bought, to=msg.sender, acting_for=getExchange(self.factory, token_addr))
@public
def tokenToTokenSwapOutput(tokens_bought: uint256, max_tokens_sold: uint256, max_eth_sold: uint256(wei), deadline: timestamp, token_addr: address) -> uint256:
    exchange_addr: address = self.factory.getExchange(token_addr)
    return self.tokenToTokenOutput(tokens_bought, max_tokens_sold, max_eth_sold, deadline, msg.sender, msg.sender, exchange_addr)

#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate[token[token(getExchange(self.factory, token_addr))]](tokens_bought, to=recipient, acting_for=getExchange(self.factory, token_addr))
@public
def tokenToTokenTransferOutput(tokens_bought: uint256, max_tokens_sold: uint256, max_eth_sold: uint256(wei), deadline: timestamp, recipient: address, token_addr: address) -> uint256:
    exchange_addr: address = self.factory.getExchange(token_addr)
    return self.tokenToTokenOutput(tokens_bought, max_tokens_sold, max_eth_sold, deadline, msg.sender, recipient, exchange_addr)

#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate[token[token(exchange_addr)]](getEthToTokenInputPrice(exchange_addr, ???), to=msg.sender, acting_for=exchange_addr)
@public
def tokenToExchangeSwapInput(tokens_sold: uint256, min_tokens_bought: uint256, min_eth_bought: uint256(wei), deadline: timestamp, exchange_addr: address) -> uint256:
    return self.tokenToTokenInput(tokens_sold, min_tokens_bought, min_eth_bought, deadline, msg.sender, msg.sender, exchange_addr)

#@ performs: reallocate[token[self.token]](tokens_sold, to=self, acting_for=msg.sender)
#@ performs: reallocate[token[token(exchange_addr)]](getEthToTokenInputPrice(exchange_addr, ???), to=recipient, acting_for=exchange_addr)
@public
def tokenToExchangeTransferInput(tokens_sold: uint256, min_tokens_bought: uint256, min_eth_bought: uint256(wei), deadline: timestamp, recipient: address, exchange_addr: address) -> uint256:
    assert recipient != self
    return self.tokenToTokenInput(tokens_sold, min_tokens_bought, min_eth_bought, deadline, msg.sender, recipient, exchange_addr)

#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate[token[token(exchange_addr)]](tokens_bought, to=msg.sender, acting_for=exchange_addr)
@public
def tokenToExchangeSwapOutput(tokens_bought: uint256, max_tokens_sold: uint256, max_eth_sold: uint256(wei), deadline: timestamp, exchange_addr: address) -> uint256:
    return self.tokenToTokenOutput(tokens_bought, max_tokens_sold, max_eth_sold, deadline, msg.sender, msg.sender, exchange_addr)

#@ performs: reallocate[token[self.token]](???, to=self, acting_for=msg.sender)
#@ performs: reallocate[token[token(exchange_addr)]](tokens_bought, to=recipient, acting_for=exchange_addr)
@public
def tokenToExchangeTransferOutput(tokens_bought: uint256, max_tokens_sold: uint256, max_eth_sold: uint256(wei), deadline: timestamp, recipient: address, exchange_addr: address) -> uint256:
    assert recipient != self
    return self.tokenToTokenOutput(tokens_bought, max_tokens_sold, max_eth_sold, deadline, msg.sender, recipient, exchange_addr)

#@ ensures: success() ==> result() == getEthToTokenInputPrice(self, eth_sold)
@public
@constant
def getEthToTokenInputPrice(eth_sold: uint256(wei)) -> uint256:
    assert eth_sold > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    return self.getInputPrice(as_unitless_number(eth_sold), as_unitless_number(self.balance), token_reserve)

#@ ensures: success() ==> result() == getEthToTokenOutputPrice(self, tokens_bought)
@public
@constant
def getEthToTokenOutputPrice(tokens_bought: uint256) -> uint256(wei):
    assert tokens_bought > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_sold: uint256 = self.getOutputPrice(tokens_bought, as_unitless_number(self.balance), token_reserve)
    return as_wei_value(eth_sold, 'wei')

@public
@constant
def getTokenToEthInputPrice(tokens_sold: uint256) -> uint256(wei):
    assert tokens_sold > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    eth_bought: uint256 = self.getInputPrice(tokens_sold, token_reserve, as_unitless_number(self.balance))
    return as_wei_value(eth_bought, 'wei')

@public
@constant
def getTokenToEthOutputPrice(eth_bought: uint256(wei)) -> uint256:
    assert eth_bought > 0
    token_reserve: uint256 = self.token.balanceOf(self)
    return self.getOutputPrice(as_unitless_number(eth_bought), token_reserve, as_unitless_number(self.balance))

#@ ensures: success() ==> result() == token(self)
@public
@constant
def tokenAddress() -> address:
    return self.token

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
