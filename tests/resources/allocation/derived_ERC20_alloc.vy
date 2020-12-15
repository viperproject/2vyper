#
# The MIT License (MIT)
#
# Copyright (c) 2015 Vitalik Buterin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# This file was adapted from https://github.com/ethereum/vyper/blob/master/examples/tokens/ERC20.vy 


# @dev Implementation of ERC-20 token standard.
# @author Takayuki Jimba (@yudetamago)
# https://github.com/ethereum/EIPs/blob/master/EIPS/eip-20.md

from vyper.interfaces import ERC20

implements: ERC20

#@ config: allocation

Transfer: event({_from: indexed(address), _to: indexed(address), _value: uint256})
Approval: event({_owner: indexed(address), _spender: indexed(address), _value: uint256})

name: public(string[64])
symbol: public(string[32])
decimals: public(uint256)
token: ERC20

balanceOf: public(map(address, uint256))
allowances: map(address, map(address, uint256))
self.allowance_to_decompose: map(address, uint256)
total_supply: uint256


#@ derived resource: token() -> ERC20.token[self.token]


#@ invariant: self.minter == old(self.minter)
#@ invariant: self.total_supply == sum(self.balanceOf)
#@ always check: implies(msg.sender != self.minter, old(self.total_supply) >= self.total_supply)
#@ always check: forall({a: address, b: address}, {self.balanceOf[a], self.balanceOf[b]}, implies(self.balanceOf[a] > old(self.balanceOf[a]) and self.balanceOf[b] < old(self.balanceOf[b]), event(Transfer(b, a, self.balanceOf[a] - old(self.balanceOf[a])))))
#@ always check: forall({a: address}, {self.balanceOf[a]}, {old(self.balanceOf[a])}, implies(old(self.balanceOf[a]) > self.balanceOf[a] and forall({b: address}, {old(self.balanceOf[b])}, {self.balanceOf[b]}, implies(b != a, self.balanceOf[b] == old(self.balanceOf[b]))), event(Transfer(a, ZERO_ADDRESS, old(self.balanceOf[a]) - self.balanceOf[a]))))
#@ always check: forall({a: address}, {self.balanceOf[a]}, {old(self.balanceOf[a])}, implies(old(self.balanceOf[a]) < self.balanceOf[a] and forall({b: address}, {self.balanceOf[b]}, {old(self.balanceOf[b])}, implies(b != a, self.balanceOf[b] == old(self.balanceOf[b]))), event(Transfer(ZERO_ADDRESS, a, self.balanceOf[a] - old(self.balanceOf[a])))))
#@ always check: forall({a: address, b: address}, {self.allowances[a][b]}, {old(self.allowances[a][b])}, implies(old(self.allowances[a][b]) < self.allowances[a][b], event(Approval(a, b, self.allowances[a][b]))))

#@ invariant: sum(allocated[wei]()) == 0
#@ invariant: allocated[token]() == self.balanceOf

#@ invariant: forall({o: address, s: address}, self.allowances[o][s] == offered[token <-> token](1, 0, o, s))

#@ invariant: forall({a: address}, allowed_to_decompose[token](a) == self.allowance_to_decompose[a])


@public
def __init__(_name: string[64], _symbol: string[32], _decimals: uint256, _token_address: address):
    self.name = _name
    self.symbol = _symbol
    self.decimals = _decimals
    self.token = ERC20(_token_address)
    log.Transfer(ZERO_ADDRESS, msg.sender, init_supply)


#@ ensures: implies(success(), result() == sum(self.balanceOf))
@public
@constant
def totalSupply() -> uint256:
    return self.total_supply


@public
@constant
def allowance(_owner: address, _spender: address) -> uint256:
    return self.allowances[_owner][_spender]


#@ performs: reallocate[token](_value, to=_to)
#@ ensures: implies(_value > old(self.balanceOf[msg.sender]), revert())
#@ check: implies(success(), event(Transfer(msg.sender, _to, _value)))
@public
def transfer(_to: address, _value: uint256) -> bool:
    self.balanceOf[msg.sender] -= _value
    #@ reallocate[token](_value, to=_to)
    self.balanceOf[_to] += _value
    log.Transfer(msg.sender, _to, _value)
    return True


#@ performs: exchange[token <-> token](1, 0, _from, msg.sender, times=_value)
#@ performs: reallocate[token](_value, to=_to)
#@ ensures: implies(_value > old(self.allowances[_from][msg.sender]), revert())
#@ check: implies(success(), event(Transfer(_from, _to, _value)))
@public
def transferFrom(_from : address, _to: address, _value: uint256) -> bool:
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowances[_from][msg.sender] -= _value
    #@ exchange[token <-> token](1, 0, _from, msg.sender, times=_value)
    #@ reallocate[token](_value, to=_to)
    log.Transfer(_from, _to, _value)
    return True


#@ performs: revoke[token <-> token](1, 0, to=_spender)
#@ performs: offer[token <-> token](1, 0, to=_spender, times=_value)
#@ check: implies(success(), event(Approval(msg.sender, _spender, _value)))
@public
def approve(_spender: address, _value : uint256) -> bool:
    #@ revoke[token <-> token](1, 0, to=_spender)
    self.allowances[msg.sender][_spender] = _value
    #@ offer[token <-> token](1, 0, to=_spender, times=_value)
    log.Approval(msg.sender, _spender, _value)
    return True


@public
@constant
def approve_to_decompose(_value: uint256) -> uint256:
    self.allowance_to_decompose[msg.sender] = _value
    return True

#@ performs: payable?[token](_value)
#@ performs: reallocate[token](_value, to=_to)
@public
def mint(_to: address, _value: uint256):
    assert msg.sender == self.minter
    assert _to != ZERO_ADDRESS

    self.token.transferFrom(msg.sender, self, _value)
    self.total_supply += _value

    #@ reallocate[token](_value, to=_to)
    self.balanceOf[_to] += _value
    log.Transfer(ZERO_ADDRESS, _to, _value)

#@ performs: payout?[token](_value, acting_For=_to)
@private
def _burn(_to: address, _value: uint256):
    assert _to != ZERO_ADDRESS
    self.total_supply -= _value
    self.balanceOf[_to] -= _value

    self.token.transfer(_to, _value)

    log.Transfer(_to, ZERO_ADDRESS, _value)

#@ performs: payout?[token](_value)
@public
def burn(_value: uint256):
    self._burn(msg.sender, _value)

#@ performs: exchange[token <-> token](1, 0, _to, msg.sender, times=min(_value, self.balanceOf[_to]))
#@ performs: payout?[token](_value)
@public
def burnFrom(_to: address, _value: uint256):
    self.allowances[_to][msg.sender] -= _value
    #@ exchange[token <-> token](1, 0, _to, msg.sender, times=min(_value, self.balanceOf[_to]))
    self.allowance_to_decompose[_to] -= _value
    self._burn(_to, _value)
