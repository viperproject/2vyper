
balanceOf: public(map(address, uint256))
allowances: map(address, map(address, uint256))
total_supply: uint256
minter: address


#@ invariant: self.minter == old(self.minter)
#@ always ensures: implies(msg.sender != self.minter, old(self.total_supply) >= self.total_supply)
#@ invariant: sum(self.balanceOf) == self.total_supply
#:: Label(ZERO)
#@ invariant: self.balanceOf[ZERO_ADDRESS] == 0


@public
def __init__(_supply: uint256):
    init_supply: uint256 = _supply
    self.balanceOf[msg.sender] = init_supply
    self.total_supply = init_supply
    self.minter = msg.sender


@public
@constant
def totalSupply() -> uint256:
    return self.total_supply


@public
@constant
def allowance(_owner : address, _spender : address) -> uint256:
    return self.allowances[_owner][_spender]


#@ ensures: self.total_supply == old(self.total_supply)
#@ ensures: forall({a: address}, {self.balanceOf[a]}, implies(a != msg.sender and a != _to, old(self.balanceOf[a]) == self.balanceOf[a]))
#:: ExpectedOutput(invariant.violated:assertion.false, ZERO)
@public
def transfer(_to : address, _value : uint256) -> bool:
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    return True


#@ ensures: implies(old(self.balanceOf[_from]) < _value, not success())
#@ ensures: implies(old(self.allowances[_from][msg.sender]) < _value, not success())
#@ ensures: self.total_supply == old(self.total_supply)
#@ ensures: forall({a: address}, {self.balanceOf[a]}, implies(a != _from and a != _to, old(self.balanceOf[a]) == self.balanceOf[a]))
#@ ensures: implies(success(), sum(self.allowances[_from]) + _value == old(sum(self.allowances[_from])))
#:: ExpectedOutput(invariant.violated:assertion.false, ZERO)
@public
def transferFrom(_from : address, _to : address, _value : uint256) -> bool:
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowances[_from][msg.sender] -= _value
    return True


#@ ensures: self.total_supply == old(self.total_supply)
@public
def approve(_spender : address, _value : uint256) -> bool:
    self.allowances[msg.sender][_spender] = _value
    return True


#@ ensures: implies(success(), self.total_supply == old(self.total_supply) + _value)
#@ ensures: forall({a: address}, {self.balanceOf[a]}, implies(a != _to, old(self.balanceOf[a]) == self.balanceOf[a]))
@public
def mint(_to: address, _value: uint256):
    assert msg.sender == self.minter
    assert _to != ZERO_ADDRESS
    self.total_supply += _value
    self.balanceOf[_to] += _value


#@ ensures: implies(success(), self.total_supply == old(self.total_supply) - _value)
#@ ensures: forall({a: address}, {self.balanceOf[a]}, implies(a != msg.sender, old(self.balanceOf[a]) == self.balanceOf[a]))
@public
def burn(_value: uint256):
    _to: address = msg.sender
    assert _to != ZERO_ADDRESS
    self.total_supply -= _value
    self.balanceOf[_to] -= _value


#@ ensures: implies(success(), self.total_supply == old(self.total_supply) - _value)
#@ ensures: forall({a: address}, {self.balanceOf[a]}, implies(a != _to, old(self.balanceOf[a]) == self.balanceOf[a]))
#@ ensures: implies(_value > old(self.allowances[_to][msg.sender]), not success())
@public
def burnFrom(_to: address, _value: uint256):
    self.allowances[_to][msg.sender] -= _value
    assert _to != ZERO_ADDRESS
    self.total_supply -= _value
    self.balanceOf[_to] -= _value