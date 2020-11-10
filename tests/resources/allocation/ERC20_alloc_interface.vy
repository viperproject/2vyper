#:: IgnoreFile(0)

# Interface for the used methods in ERC20

#@ interface

#@ resource: token()

# Events

Transfer: event({_from: address, _to: address, _value: uint256})
Approval: event({_owner: address, _spender: address, _value: uint256})

#@ ghost:
    #@ def balanceOf() -> map(address, uint256): ...
    #@ def minter() -> address: ...
    #@ def total_supply() -> address: ...
    #@ def allowances() -> map(address, map(address, uint256)): ...

#@ invariant: minter(self) == old(minter(self))
#@ invariant: total_supply(self) == sum(balanceOf(self))

#@ invariant: sum(allocated[wei]()) == 0
#@ invariant: allocated[token]() == balanceOf(self)
#@ invariant: forall({a: address}, {allocated[creator(token)](a)}, allocated[creator(token)](a) == (1 if a == minter(self) else 0))

#@ invariant: forall({o: address, s: address}, self.allowances[o][s] == offered[token <-> token](1, 0, o, s))

#@ caller private: balanceOf(self)[caller()] - sum(allowance(self)[caller()])
#@ caller private: conditional(sum(allowance(self)[caller()]) == 0, allowance(self)[caller()])

# Functions

# performs: create[token](init_supply)  # This is not possible to write!
#@ performs: create[token](_supply * 10 ** _decimals)
#@ performs: create[creator(token)](1)
#@ ensures: success() ==> minter(self) == msg.sender
#@ ensures: success() ==> total_supply(self) == _supply * 10 ** _decimals
#@ ensures: success() ==> balanceOf(self)[msg.sender] == _supply * 10 ** _decimals
@public
def __init__(_name: string[64], _symbol: string[32], _decimals: uint256, _supply: uint256):
    raise "Not implemented"

#@ ensures: success() ==> result() == total_supply(self)
@constant
@public
def totalSupply() -> uint256:
    raise "Not implemented"

#@ ensures: success() ==> result() == allowance(self)[_owner][_spender]
@constant
@public
def allowance(_owner: address, _spender: address) -> uint256:
    raise "Not implemented"

#@ ensures: success() ==> result() == balanceOf(self)[arg0]
@constant
@public
def balanceOf(arg0: address) -> uint256:
    raise "Not implemented"

#@ performs: reallocate[token](_value, to=_to)
#@ ensures: _value > old(balanceOf(self)[msg.sender]) ==> revert()
#@ ensures: success() ==> balanceOf(self)[msg.sender] == old(balanceOf(self)[msg.sender]) - _value
#@ ensures: success() ==> balanceOf(self)[to] == old(balanceOf(self)[to]) + _value
#@ ensures: forall({a: address}, a != msg.sender and a != _to ==> balanceOf(self)[a] == old(balanceOf(self)[a]))
#@ ensures: allowance(self) == old(allowance(self))
@public
def transfer(_to: address, _value: uint256) -> bool:
    raise "Not implemented"

#@ performs: exchange[token <-> token](1, 0, _from, msg.sender, times=_value)  # Exchanges deal with allowance
#@ performs: reallocate[token](_value, to=_to)
#@ ensures: _value > old(self.allowances[_from][msg.sender]) ==> revert()
#@ ensures: _value > old(balanceOf(self)[_from]) ==> revert()
#@ ensures: success() ==> balanceOf(self)[_to] == old(balanceOf(self)[_to]) + _value
#@ ensures: success() ==> balanceOf(self)[_from] == old(balanceOf(self)[_from]) - _value
#@ ensures: forall({a: address}, a != _from and a != _to ==> balanceOf(self)[a] == old(balanceOf(self)[a]))
#@ ensures: success() ==> allowances(self)[_from][msg.sender] == old(allowances(self)[_from][msg.sender]) - _value
#@ ensures: forall({a: address}, a != _from ==> allowances(self)[a] == old(allowances(self)[a]))
#@ ensures: forall({a: address}, a != msg.sender ==> allowances(self)[msg.sender][a] == old(allowances(self)[msg.sender][a]))
@public
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    raise "Not implemented"

#@ performs: revoke[token <-> token](1, 0, to=_spender)
#@ performs: offer[token <-> token](1, 0, to=_spender, times=_value)
#@ ensures: success() ==> allowances(self)[msg.sender][_spender] == _value
#@ ensures: forall({a: address}, a != msg.sender ==> allowances(self)[a] == old(allowances(self)[a]))
#@ ensures: forall({a: address}, a != _spender ==> allowances(self)[msg.sender][a] == old(allowances(self)[msg.sender][a]))
#@ ensures: balanceOf(self) == old(balanceOf(self))
@public
def approve(_spender: address, _value: uint256) -> bool:
    raise "Not implemented"

#@ performs: destroy[token](_value)
#@ ensures: success() ==> balanceOf(self)[msg.sender] == old(balanceOf(self)[msg.sender]) - _value
#@ ensures: forall({a: address}, a != msg.sender ==> balanceOf(self)[a] == old(balanceOf(self)[a]))
#@ ensures: allowance(self) == old(allowance(self))
@public
def burn(_value: uint256):
    raise "Not implemented"

#@ performs: exchange[token <-> token](1, 0, _to, msg.sender, times=_value)  # Exchanges deal with allowance
#@ performs: destroy[token](_value)
#@ ensures: success() ==> balanceOf(self)[_from] == old(balanceOf(self)[_from]) - _value
#@ ensures: forall({a: address}, a != _from ==> balanceOf(self)[a] == old(balanceOf(self)[a]))
#@ ensures: success() ==> allowances(self)[_from][msg.sender] == old(allowances(self)[_from][msg.sender]) - _value
#@ ensures: forall({a: address}, a != _from ==> allowances(self)[a] == old(allowances(self)[a]))
#@ ensures: forall({a: address}, a != msg.sender ==> allowances(self)[msg.sender][a] == old(allowances(self)[msg.sender][a]))
@public
def burnFrom(_from: address, _value: uint256):
    raise "Not implemented"

#@ performs: create[token](_value, to=_to)
#@ ensures: msg.sender != self.minter ==> revert()
#@ ensures: success() ==> balanceOf(self)[_to] == old(balanceOf(self)[_to]) + _value
#@ ensures: forall({a: address}, a != _to ==> balanceOf(self)[a] == old(balanceOf(self)[a]))
#@ ensures: allowance(self) == old(allowance(self))
@public
def mint(_to: address, _value: uint256):
    raise "Not implemented"

@constant
@public
def name() -> string[64]:
    raise "Not implemented"

@constant
@public
def symbol() -> string[32]:
    raise "Not implemented"

@constant
@public
def decimals() -> uint256:
    raise "Not implemented"