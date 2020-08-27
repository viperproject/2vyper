# Interface for the used methods in Compound cERC20
#
# Events

#@ interface

Transfer: event({_from: address, _to: address, _value: uint256})
Approval: event({_owner: address, _spender: address, _value: uint256})

# Functions

@constant
@public
def totalSupply() -> uint256:
    raise "Not implemented"

@constant
@public
def allowance(_owner: address, _spender: address) -> uint256:
    raise "Not implemented"

#@ ensures: success() ==> storage(msg.sender) == old(storage(msg.sender))
@public
def transfer(_to: address, _value: uint256) -> bool:
    raise "Not implemented"

@public
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    raise "Not implemented"

@public
def approve(_spender: address, _value: uint256) -> bool:
    raise "Not implemented"

@public
def burn(_value: uint256):
    raise "Not implemented"

@public
def burnFrom(_to: address, _value: uint256):
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

@constant
@public
def balanceOf(arg0: address) -> uint256:
    raise "Not implemented"

@public
def mint(mintAmount: uint256) -> uint256:
    raise "Not implemented"