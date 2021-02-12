#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# This file is translated Solidity contract from:
# https://github.com/vittominacori/erc1363-payable-token/blob/7f8a1530b415408c9c7e4d02a2f5891ace33e4e9/contracts/token/ERC1363/ERC1363.sol


#@ config: allocation, no_derived_wei_resource, trust_casts

import tests.resources.allocation.ERC1363.IERC1363Spender_alloc as IERC1363Spender
import tests.resources.allocation.ERC1363.IERC1363_alloc as not_used
import tests.resources.language.inter_contract.IERC1363_alloc_declare_fail as IERC1363_alloc

# @dev Implementation of ERC-1363 token standard
implements: IERC1363_alloc

contract IERC1363Receiver:
    def onTransferReceived(operator: address, sender: address, amount: uint256, data: bytes[1024]) -> bytes32: modifying


Transfer: event({_from: indexed(address), _to: indexed(address), _value: uint256})
Approval: event({_owner: indexed(address), _spender: indexed(address), _value: uint256})

name: public(string[64])
symbol: public(string[32])
decimals: public(uint256)

# NOTE: By declaring `balanceOf` as public, vyper automatically generates a 'balanceOf()' getter
#       method to allow access to account balances.
#       The _KeyType will become a required parameter for the getter and it will return _ValueType.
#       See: https://vyper.readthedocs.io/en/v0.1.0-beta.8/types.html?highlight=getter#mappings
balanceOf: public(map(address, uint256))
allowances: map(address, map(address, uint256))
total_supply: uint256
minter: address

# Equals to `bytes4(keccak256("onTransferReceived(address,address,uint256,bytes)"))`
# which can be also obtained as `IERC1363Receiver(0).onTransferReceived.selector`
_ERC1363_RECEIVED: constant(bytes32) = 0x0000000000000000000000000000000000000000000000000000000088a7ca5c

# Equals to `bytes4(keccak256("onApprovalReceived(address,uint256,bytes)"))`
# which can be also obtained as `IERC1363Spender(0).onApprovalReceived.selector`
_ERC1363_APPROVED: constant(bytes32) = 0x000000000000000000000000000000000000000000000000000000007b04a2d0

#@ ghost:
    #@ @implements
    #@ def balanceOf() -> map(address, uint256): self.balanceOf
    #@ @implements
    #@ def minter() -> address: self.minter
    #@ @implements
    #@ def total_supply() -> uint256: self.total_supply
    #@ @implements
    #@ def allowances() -> map(address, map(address, uint256)): self.allowances

#@ always check: implies(msg.sender != self.minter, old(self.total_supply) >= self.total_supply)
#@ always check: forall({a: address, b: address}, {self.balanceOf[a], self.balanceOf[b]}, implies(self.balanceOf[a] > old(self.balanceOf[a]) and self.balanceOf[b] < old(self.balanceOf[b]), event(Transfer(b, a, self.balanceOf[a] - old(self.balanceOf[a])))))
#@ always check: forall({a: address}, {self.balanceOf[a]}, {old(self.balanceOf[a])}, implies(old(self.balanceOf[a]) > self.balanceOf[a] and forall({b: address}, {old(self.balanceOf[b])}, {self.balanceOf[b]}, implies(b != a, self.balanceOf[b] == old(self.balanceOf[b]))), event(Transfer(a, ZERO_ADDRESS, old(self.balanceOf[a]) - self.balanceOf[a]))))
#@ always check: forall({a: address}, {self.balanceOf[a]}, {old(self.balanceOf[a])}, implies(old(self.balanceOf[a]) < self.balanceOf[a] and forall({b: address}, {self.balanceOf[b]}, {old(self.balanceOf[b])}, implies(b != a, self.balanceOf[b] == old(self.balanceOf[b]))), event(Transfer(ZERO_ADDRESS, a, self.balanceOf[a] - old(self.balanceOf[a])))))
#@ always check: forall({a: address, b: address}, {self.allowances[a][b]}, {old(self.allowances[a][b])}, implies(old(self.allowances[a][b]) < self.allowances[a][b], event(Approval(a, b, self.allowances[a][b]))))


@public
def __init__(_name: string[64], _symbol: string[32], _decimals: uint256, _supply: uint256):
    init_supply: uint256 = _supply * 10 ** _decimals
    self.name = _name
    self.symbol = _symbol
    self.decimals = _decimals
    self.balanceOf[msg.sender] = init_supply
    self.total_supply = init_supply
    #@ create[_token](init_supply)
    self.minter = msg.sender
    #@ create[creator(_token)](1)
    log.Transfer(ZERO_ADDRESS, msg.sender, init_supply)


#@ ensures: implies(success(), result() == sum(self.balanceOf))
@public
@constant
def totalSupply() -> uint256:
    """
    @dev Total number of tokens in existence.
    """
    return self.total_supply


@public
@constant
def allowance(_owner: address, _spender: address) -> uint256:
    """
    @dev Function to check the amount of tokens that an owner allowed to a spender.
    @param _owner The address which owns the funds.
    @param _spender The address which will spend the funds.
    @return An uint256 specifying the amount of tokens still available for the spender.
    """
    return self.allowances[_owner][_spender]


@private
def _transfer(_msg_sender: address, _to: address, _value: uint256) -> bool:
    """
    @dev Transfer token for a specified address
    @param _to The address to transfer to.
    @param _value The amount to be transferred.
    """
    # NOTE: vyper does not allow underflows
    #       so the following subtraction would revert on insufficient balance
    self.balanceOf[_msg_sender] -= _value
    #@ reallocate[_token](_value, to=_to, actor=_msg_sender)
    self.balanceOf[_to] += _value
    log.Transfer(_msg_sender, _to, _value)
    return True


#@ ensures: implies(_value > old(self.balanceOf[msg.sender]), revert())
#@ check: implies(success(), event(Transfer(msg.sender, _to, _value)))
@public
def transfer(_to: address, _value: uint256) -> bool:
    return self._transfer(msg.sender, _to, _value)


@private
def _transferFrom(_msg_sender: address, _from : address, _to: address, _value: uint256) -> bool:
    """
     @dev Transfer tokens from one address to another.
          Note that while this function emits a Transfer event, this is not required as per the specification,
          and other compliant implementations may not emit the event.
     @param _from address The address which you want to send tokens from
     @param _to address The address which you want to transfer to
     @param _value uint256 the amount of tokens to be transferred
    """
    # NOTE: vyper does not allow underflows
    #       so the following subtraction would revert on insufficient balance
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    # NOTE: vyper does not allow underflows
    #      so the following subtraction would revert on insufficient allowance
    self.allowances[_from][_msg_sender] -= _value
    #@ exchange[_token <-> _token](1, 0, _from, _msg_sender, times=_value)
    #@ reallocate[_token](_value, to=_to, actor=_msg_sender)
    log.Transfer(_from, _to, _value)
    return True


#@ ensures: implies(_value > old(self.allowances[_from][msg.sender]), revert())
#@ check: implies(success(), event(Transfer(_from, _to, _value)))
@public
def transferFrom(_from : address, _to: address, _value: uint256) -> bool:
    return self._transferFrom(msg.sender, _from, _to, _value)


@private
def _approve(_msg_sender: address, _spender: address, _value : uint256) -> bool:
    """
    @dev Approve the passed address to spend the specified amount of tokens on behalf of msg.sender.
         Beware that changing an allowance with this method brings the risk that someone may use both the old
         and the new allowance by unfortunate transaction ordering. One possible solution to mitigate this
         race condition is to first reduce the spender's allowance to 0 and set the desired value afterwards:
         https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    @param _spender The address which will spend the funds.
    @param _value The amount of tokens to be spent.
    """
    #@ revoke[_token <-> _token](1, 0, to=_spender)
    self.allowances[_msg_sender][_spender] = _value
    #@ offer[_token <-> _token](1, 0, to=_spender, times=_value)
    log.Approval(_msg_sender, _spender, _value)
    return True


#@ check: implies(success(), event(Approval(msg.sender, _spender, _value)))
@public
def approve(_spender: address, _value : uint256) -> bool:
    return self._approve(msg.sender, _spender, _value)


@public
def mint(_to: address, _value: uint256):
    """
    @dev Mint an amount of the token and assigns it to an account.
         This encapsulates the modification of balances such that the
         proper events are emitted.
    @param _to The account that will receive the created tokens.
    @param _value The amount that will be created.
    """
    assert msg.sender == self.minter
    assert _to != ZERO_ADDRESS
    self.total_supply += _value
    #@ create[_token](_value, to=_to)
    self.balanceOf[_to] += _value
    log.Transfer(ZERO_ADDRESS, _to, _value)


@private
def _burn(_to: address, _value: uint256):
    """
    @dev Internal function that burns an amount of the token of a given
         account.
    @param _to The account whose tokens will be burned.
    @param _value The amount that will be burned.
    """
    assert _to != ZERO_ADDRESS
    self.total_supply -= _value
    self.balanceOf[_to] -= _value
    #@ destroy[_token](_value)
    log.Transfer(_to, ZERO_ADDRESS, _value)


@public
def burn(_value: uint256):
    """
    @dev Burn an amount of the token of msg.sender.
    @param _value The amount that will be burned.
    """
    self._burn(msg.sender, _value)


@public
def burnFrom(_to: address, _value: uint256):
    """
    @dev Burn an amount of the token from a given account.
    @param _to The account whose tokens will be burned.
    @param _value The amount that will be burned.
    """
    self.allowances[_to][msg.sender] -= _value
    #@ exchange[_token <-> _token](1, 0, _to, msg.sender, times=min(_value, self.balanceOf[_to]))
    self._burn(_to, _value)


@private
def _checkAndCallTransfer(operator: address, sender: address, recipient: address, amount: uint256, data: bytes[1024]) -> bool:
    if not recipient.is_contract:
        return False
    retval: bytes32 = IERC1363Receiver(recipient).onTransferReceived(operator, sender, amount, data)
    return retval == _ERC1363_RECEIVED


@private
def _checkAndCallApprove(sender: address, spender: address, amount: uint256, data: bytes[1024]) -> bool:
    if not spender.is_contract:
        return False

    retval: bytes32 = IERC1363Spender(spender).onApprovalReceived(sender, amount, data)
    return retval == _ERC1363_APPROVED


#:: ExpectedOutput(interface.resource:resource.address.self)
#@ performs: reallocate[_token](amount, to=recipient)
@public
def transferAndCall(recipient: address, amount: uint256, data: bytes[1024]) -> bool:
    self._transfer(msg.sender, recipient, amount)
    cond: bool = self._checkAndCallTransfer(msg.sender, msg.sender, recipient, amount, data)
    assert cond, "ERC1363: _checkAndCallTransfer reverts"
    return True


#:: ExpectedOutput(interface.resource:resource.address.self)
#@ performs: exchange[_token <-> _token](1, 0, sender, msg.sender, times=amount)
#@ performs: reallocate[_token](amount, to=recipient)
@public
def transferFromAndCall(sender: address, recipient: address, amount: uint256, data: bytes[1024]) -> bool:
    self._transferFrom(msg.sender, sender, recipient, amount)
    cond: bool = self._checkAndCallTransfer(msg.sender, sender, recipient, amount, data)
    assert cond, "ERC1363: _checkAndCallTransfer reverts"
    return True


#:: ExpectedOutput(interface.resource:resource.address.self)
#@ performs: revoke[_token <-> _token](1, 0, to=spender)
#@ performs: offer[_token <-> _token](1, 0, to=spender, times=amount)
@public
def approveAndCall(spender: address, amount: uint256, data: bytes[1024]) -> bool:
    self._approve(msg.sender, spender, amount)
    cond: bool = self._checkAndCallApprove(msg.sender, spender, amount, data)
    assert cond, "ERC1363: _checkAndCallApprove reverts"
    return True
