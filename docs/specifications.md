This document briefly describes most of the specification constructs currently available in 2vyper. For more in-depth descriptions, read Robin Sierra's and Christian Bräm's MSc theses (or check out the [tests folder](../tests/resources) for example usages).

# Configuration
2vyper does not explicitly track gas consumption; instead, it assumes that any function can fail at any point due to lack of gas. To configure 2vyper to ignore reverts because of gas (i.e., to assume this never happens), write 
```
#@ config: no_gas
```

2vyper does accurately model reverts because of arithmetic overflows. To assume overflows do not happen, write

```
#@ config: no_overflows
```

2vyper will by default expect Vyper contracts that fit the version of Vyper that is currently installed. To fix a specific Vyper version in the contract, use the version pragma:
```
# @version 0.2.x
```

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
These two-state assertions must be reflexive and transitive.

## Specification functions

Execution state:
- ``success()``: Is true if the function returned successfully (without reverting)
- ``result()``: the value returned by the current function
- ``event(e, n)``: Is true if the event ``e`` has been fired exactly ``n`` times since the last public state. ``n`` defaults to 1. See below for information about specifications about events.
- ``locked("lock")``: Is true if the "lock" (created by annotation ``@nonreentrant("lock")``) is currently locked. See below for information about specifications about locks. 

Contract ghost state:
- ``sent()``: Returns a ``map(address, wei_value)`` that contains the amount of Ether the current contract has sent to other addresses.
- ``received()``:  Returns a ``map(address, wei_value)`` that contains the amount of Ether the current contract has received from other addresses.

Logical connectives:
- ``implies(e, P)``: Logical implication. Can also be written ``e ==> P``. 
- ``forall({x: T1, y: T2}, triggers, P)``: Universal quantification, i.e., ``P`` holds for all values ``x`` and ``y`` of types ``T1`` and ``T2``. ``triggers`` is an optional hint to the SMT solver on when to instantiate the quantifier, and should the form ``{e1, ..., en}`` where the ``e``s must be some expression that, as a whole, contain all quantified variables. 

Convenience functions:
- ``sum(e)``: Sum of all values in map ``e``.
- ``storage(a)``: Refers to the entire storage of address ``a``. Useful e.g. to express that some contract's state has not changed (``storage(self) == old(storage(self))``).

## Loops and private functions

By defaults, loops are unrolled, and calls to private functions are inlined. If this is not desired, loops can be verified in terms of invariants; to achieve this, simply annotate a loop with an invariant as follows:
```
for i in range(NUM_TOKENS):
    #@ invariant: self.ownerToNFTokenCount[ZERO_ADDRESS] == 0
```

Similarly, private functions will not be inlined if they are annotated with a precondition:
```
#@ requires: self.val >= 0
@private
def inc_val() -> address:
    ...
```
For more information about loop invariants and private functions, see Christian Bräm's thesis.

## Pure functions
Constant functions (views) that do not log events can be annotated as pure, meaning that they can be used inside other specifications like postconditions or invariants (note that pure has a different meaning here than the pure decorator in Vyper 0.2):

```
#@ pure
@private
@constant
def get_a() -> int128:
    return self.a
    
#@ invariant: result(self.get_a()) >= 0
```

References to such a function can either refer to their result, as shown in the example, which is valid only if the function does not revert when called with the used arguments, or they can explicitly refer to the success of the function call by writing ``success(self.get_a())`` (which returns a boolean). For more information, see Christian Bräm's thesis.


# Interfaces
2vyper can prove invariants between multiple contracts. Such invariants have to be declared on a primary contract, and are verified against the interfaces of the other involved contracts. 
Contracts can be explicitly marked to be interfaces by writing
```
#@ interface
```
Like actual contracts, interfaces can be annotated with invariants, and interface functions with postconditions. Instead of referring to concrete contract state, interfaces can declare ghost functions:

```
#@ ghost:
    #@ def user_balance(a: address) -> int128: ...
    
#@ invariant: forall({a: address}, user_balance(self, a) >= -1000)
```

Contracts that implement such an interface then have to provide an implementation (i.e., some expression) for each ghost function:
```
#@ ghost:
    #@ @implements
    #@ def user_balance(a: address) -> int128: self.amounts[a]
```

Interfaces can also state that they offer conceptually private state to their clients (e.g., a token contract's balance may be private state of its clients). For example, the following interface states that the balance of each address is their private state and cannot be changed by others:
```
#@ ghost:
    #@ def _balance() -> map(address, uint256): ...

#@ caller private: _balance(self)[caller()]
```

This is a special case of a local check (see below). For more information on proving inter-contract invariants, see Christian Bräm's thesis and/or the examples in [this folder](../tests/resources/language/inter_contract).


# Advanced specifications

2vyper contains some specification constructs specifically created for the domain of smart contracts. For more information on these, see Robin Sierra's thesis.

## General postconditions
It is possible to state that some (two-state) postconditions hold for every function in the contract. This is especially useful to specify the behavior of locks that the contract implements either manually or through ``@nonreentrant`` annotations. E.g., one can specify that the lock ``"lock"`` ensures that, when set, the field ``self.val`` is not changed and no Ether is set to anyone, as follows:

```
#@ preserves:
    #@ always ensures: old(locked('lock')) ==> locked('lock')
    #@ always ensures: old(locked('lock')) ==> sent() == old(sent())
    #@ always ensures: old(locked('lock')) ==> self.val == old(self.val)
```


## Local checks
Local checks are two-state assertions that must hold for each local segment of the contract (i.e., for each segment code that is executed without interruption or calls to the outside). They are especially useful to specify access control properties. Here is an example for a kind of token contract:

```
#@ always check: msg.sender != self.minter ==> sum(self.balanceOf) == old(sum(self.balanceOf))
```

This states that for each segment of the contract, the sum of balances must not change unless the function has been invoked by ``self.minter``. Essentially, this means that only the minter can change the number of existing tokens.

Local checks are also useful to specify events, here is an example:
```
#@ always check: forall({a: address, b: address}, implies(self.balanceOf[a] > old(self.balanceOf[a]) and self.balanceOf[b] < old(self.balanceOf[b]), event(Transfer(b, a, self.balanceOf[a] - old(self.balanceOf[a])))))
```
This states that, if in a segment, the balances of ``a`` increases and that of ``b`` decreases, the event ``Transfer(a, b, v)`` must be triggered (where ``v`` is the difference in ``a``'s balance). 

Checks can also be applied to a single function by using them as a function annotation and removing the ``àlways``. For example, the following check ensures that (every segment of the function) triggers the ``Approval`` event:

```
#@ check: implies(success(), event(Approval(msg.sender, _spender, _value)))
@public
def approve(_spender: address, _value : uint256) -> bool:
    ...
```

## Resources
2vyper allows stating that a contract offers a resource (e.g. a token) and to write specifications in terms of resource transfers. Some examples can be found in [this folder](../tests/resources/allocation), and some specification constructs are explained [here](allocation.md); more documentation on this will follow.
