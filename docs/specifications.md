Bla

# Configuration

# Basic specifications

2vyper supports most standard specification constructs as well as standard logical connectives, which we will show in this section. For specifiying concepts like locks and access control, 2vyper uses custom specification constructs, which we will show later.

## Postconditions

Postconditions can be written as function annotations using the ``ensures`` keyword. Here is an example from an ERC20 contract:
```
#@ ensures: implies(success(), result() == sum(self.balanceOf))
@public
@constant
def totalSupply() -> uint256:
    return self.total_supply
```
This postcondition states that, if the function succeeds (i.e., does not revert), then the returned result is equal to the sum of the values of the ``balanceOf`` map. This also shows some of the special specification functions 2vyper offers; see below for other examples.

## Invariants and history constraints

Contract invariants that must hold in every state while the contract is not executing (i.e., in every public state) can be written as follows:
```
#@ invariant: self.total_supply == sum(self.balanceOf)
```

Additionally, invariants can contain two-state assertions that specify how the contract state can change over time, i.e., between public states. This can for example be used to specify that some values must stay constant, or cannot decrease. One can use the ``old(e)`` function to refer to the old value of expression ``e``. Here is an example from ERC20 that states that the value of the ``minter`` field can never change:
```
#@ invariant: self.minter == old(self.minter)
```

## Specification functions

Execution state:
- success(): 
- revert():
- result():
- event(): 

Contract ghost state:
- sent()
- received()

Logical connectives:
- implies(e1, P): 
- forall({x: T1, y: T2}, { e }, P): 

Convenience functions:
- sum()

## Loops and private functions

## Pure functions

# Interfaces
caller-private

# Advanced specifications

## General postconditions
locks

## Local checks
events, access control

## Resources
