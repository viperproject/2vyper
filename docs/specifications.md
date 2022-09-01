# Specifications

As an example of a (partial) annotated contract, see this part of the auction contract written with Vyper 0.1.0b16 syntax:

```python
beneficiary: public(address)
auctionStart: public(timestamp)
auctionEnd: public(timestamp)

highestBidder: public(address)
highestBid: public(wei_value)

ended: public(bool)

pendingReturns: public(map(address, wei_value))

#@ invariant: old(self.ended) ==> self.ended
#@ invariant: not self.ended ==> 
#@   sum(self.pendingReturns) + self.highestBid <= self.balance

# more specification

@public
def __init__(_beneficiary: address, _bidding_time: timedelta):
    assert _beneficiary != ZERO_ADDRESS
    
    self.beneficiary = _beneficiary
    self.auctionStart = block.timestamp
    self.auctionEnd = self.auctionStart + _bidding_time


#@ ensures: success() ==> self.highestBid > old(self.highestBid)
@public
@payable
def bid():
    assert block.timestamp < self.auctionEnd
    assert not self.ended
    assert msg.value > self.highestBid
    assert msg.sender != self.beneficiary

    self.pendingReturns[self.highestBidder] += self.highestBid
    self.highestBidder = msg.sender
    self.highestBid = msg.value
    
# more functions
```

The code first declares the contract's fields, and subsequently defines its constructor and other functions. 
Specifications are written in the contract as special comments starting with ``#@}``. Some specifications are on the level of the contract (such as the invariants, i.e. transitive segment constraints, written after the field declarations in the example), while others refer to specific functions (such as the postcondition of function ``bid``, declared using the ``ensures`` keyword). All specifications can refer to specification functions, like ``old(...)``, ``success()``, or  ``sum(...)``.

We will now first show the most important configuration options 2vyper supports inside a given contract. Then, we will
describe the syntax for the specification constructs we introduce in the paper, and subsequently explain the most important specification functions. 
Note that the terminology used in the tool, and the resulting syntax of some specification constructs, differs from the one used in the paper, but all specification constructs described in the paper are implemented in the tool. 

## Configuration:
2vyper supports different versions of the Vyper language, up until version 0.2.11, which was the most recent version when the paper was submitted. 
Contracts can contain version pragmas to force the use of a specific version:
```
# @version 0.2.x
```
If no version pragma is present, 2vyper assumes the code is written in Vyper 0.1.0b16, which is the version used in all examples.

Additionally, 2vyper supports different per-file configuration options, which can be written inside a contract as follows:
```
#@ config: no_overflows
```
Different options must be separated by commas. For example, the option ``no_overflows`` shown above instructs the verifier to assume that there are no reverts due to integer over- or underflows.
Important options used in the examples are:
  - ``allocation``: enables the resource reasoning described in Sec. 5 of the paper.
  - ``no_derived_wei_resource``: As described in the paper, when the resource system is enabled, by default, the verifier implicitly assumes that every contract declares a derived resource for Ether, i.e. it assumes that Ether sent to a contract should still logically belong to the sender. This option disables this implicitly-declared resource.
  - ``no_performs``: As described in Sec. 5.4 of the paper, when using the resource system, functions must declare each resource effect they directly cause; the syntax for doing this in 2vyper starts with the keyword ``#@ performs: ...``. This configuration option disables the obligation to declare all resource effects; i.e. it allows users to let 2vyper check the resource properties as described in Sec. 5.1-5.3 without the potential overhead of writing effects-clauses as client specifications. 

## Central specification constructs
The central specification constructs we introduce in Sec. 3 in the paper can be declared in the tool as follows:

### Segment constraints:
A segment constraint P can be written in the tool using the syntax ``#@ always check: P``. As an example, the line 
```
#@ always check: implies(msg.sender != self.minter, 
#@   old(self.total_supply) == self.total_supply)
```
states that at the end of each segment, the value of the ``total_supply`` field must not have changed unless the function was claled by ``self.minter``. 

### Transitive segment constraints: 
A transitive segment constraint P can be written in the tool using the syntax ``#@ invariant: P``.
As an example, the partial auction contract above contains two transitive segment constraints: one that states that once the auction has ended, it will never be restarted; the second is a single-state transitive segment constraint that states that while the auction has not ended, the contract's balance must be sufficient to pay the pending returns and pay the seller the current highest bid.

### Function constraints: 
A function constraint P can be written in the tool using the syntax ``#@ preserves: #@ always ensures: P``.
For example, the following function constraint
```
#@ preserves:
    #@ always ensures: locked("lock") and old(self.state) == 3 ==> 
    #@   self.state == old(self.state)
```
ensures that, if the contract was in state 3 at the beginning of the function, and lock "lock" is locked, then the value of ``self.state`` must be unchanged at the end of the function. 

### Specifications for collaborating contracts
The specification constructs for modularly verifying collaborating contracts that we introduce in Sec. 4 in the paper can be declared in the tool as follows:

#### Interfaces:
Vyper contracts can interact with other contracts through interfaces, and can declare interfaces themselves. Interfaces are contracts in separate files that must be marked with the line
```
#@ interface
```
As described in the paper, in 2vyper, interfaces can be annotated with transitive segment constraints and privacy constraints, and functions in interfaces can be annotated as usual with postconditions. To allow reasoning about the state of a contract that implements an interface, without fixing how exactly this state is implemented in the contract, 2vyper allows declaring abstract ``ghost`` functions that each contract that implements an interface must then define. For example, an interface can declare that a contract's state contains a notion of a balance by making the following declaration:
```
#@ ghost:
    #@ def balance() -> uint256: ...
```
A contract that implements the interface then has to define how this notion of balance is represented in the actual contract state. For example, the following declaration
```
#@ ghost:
    #@ @implements
    #@ def balance() -> uint256: self.balance
```
states that the field ``self.balance`` represents this notion of balance. 

#### Inter-contract invariants
In 2vyper, standard transitive segment constraints that are declared using the ``invariant`` keyword must not refer to other contracts. Transitive segment constraints that do refer to other contracts, i.e., inter-contract invariants as described in the paper, must be specially marked as such; a declaration of an inter-contract invariant P looks like this:
```
#@ inter contract invariant: P
```

#### Privacy constraints: 
As stated above and in the paper, interfaces can contain privacy constraints, which are special segment constraints of the form ``forall a. msg.sender != a ==> P``, where P is reflexive and transitive. 2vyper implements a special case of this feature: 
The declaration
```
#@ caller private: mapping(self)[caller()]
```
expresses the privacy constraint ``forall a. msg.sender != a ==> mapping(self) =old(mapping(self))``. More generally, 
```
#@ caller private: e
```
where ``e`` contains ``caller()``, expresses that ``e`` can only be modified by the caller; i.e. it represents a privacy constraint stating that ``forall a. msg.sender != a ==> e[a/caller()] = old(e[a/caller()])``. 


### Resources
The specifications for the resource reasoning described in Sec. 5 of the paper can be written as follows (note that, as described above, resource reasoning has to be enabled for each contract by using the ``allocation`` configuration option):

#### Resource declarations:
A contract can, for example, declare a resource called ``token`` as follows:
```
#@ resource: token()
```

As briefly mentioned in the paper, 2vyper also supports reasoning about resources that have identifiers, which can be declared as follows:
```
#@ resource: token(id: uint256)
```

#### Ghost commands and ghost state
Resource ghost commands can simply be written as commands starting with ``#@``. For example, the command
```
#@ create[token](init_supply)
```
creates ``init_supply`` new instances of the ``token`` resource (and the verifier will automatically check the conditions that must be fulfilled for this to be allowed, e.g. in this case that the caller of the function has the right to create new instances of this resource). Similarly, 
```
#@ exchange[token <-> nothing](1, 0, f, msg.sender, times=v)
```
performs an exchange of 1 instance of resource ``token`` from ``f`` against zero instances of resource ``nothing`` from ``msg.sender``, and does so ``v`` times. The syntax matches the terminology used in the paper, with the exception of the command for transferring resources, which is ``transfer_R(f, t, a)`` in the paper but is written as 
```
#@ reallocate[R](a, to=t)
```
in the tool. Note that the sender of the transfer defaults to ``msg.sender``, and the resource defaults to ``wei``. Similarly, the map ``balances_R`` from the paper that contains the balances of all contracts in resource ``R`` is written as ``allocated[R]`` in the tool.

#### Effects-clauses
As described in the paper, functions must declare which effects they cause. They can be declared in the tool using the ``performs`` keyword:
```
#@ performs: exchange[token <-> token](1, 0, f, msg.sender, times=v)
#@ performs: reallocate[token](v, to=_to)
@public
def transferFrom(f: address, _to: address, v: uint256) -> bool:
    ...
```

The effects are named as in the paper, except for the transfer-effect, which, as shown in the example, is again called a reallocate-effect in the tool. 
Additionally, the effects for creating and destroying derived resources are called ``payable`` and ``payout``, respectively, in the tool.

#### Derived resources
A contract can declare a resource ``dtoken`` that is derived from resource ``token`` declared by contract ``self.other`` as follows:
```
#@ derived resource: dtoken() -> token[self.other]
```

## Specification functions

Throughout the aforementioned specification constructs, the following specification functions can be used (among others):
  - ``success()``, used in postconditions, is true iff the function returned successfully (without reverting); this can be used in function postconditions to specify under which conditions functions should terminate successfully, and therefore specify certain kinds of liveness properties.
  - ``result()``, used in postconditions, is the value returned by the current function
  - ``event(e, n)`` is true iff the event ``e`` has been fired exactly ``n`` times since the beginning of the current local segment. ``n`` defaults to 1.
  - ``locked("lock")``  is true iff the "lock" (created by the standard Vyper function annotation ``@nonreentrant("lock")``) is currently locked
  - ``sent()`` returns a map that contains the amount of Ether the current contract has sent to other addresses
  - ``received()`` returns a map that contains the amount of Ether the current contract has received from other addresses.
  - ``sum(e)`` denotes the sum of all values in map ``e``
  - ``implies(e, P)`` denotes logical implication and can also be written as ``e ==> P``
  - ``forall({x: T1, y: T2}, triggers, P)`` denotes universal quantification, i.e. ``P`` holds for all values ``x`` and ``y`` of types ``T1`` and ``T2``. ``triggers`` is an optional hint to the SMT solver on when to instantiate the quantifier, and should have the form ``{e1, ..., en}``, where the ``e``s must be some expression that, as a whole, contain all quantified variables.
  - ``accessible(o, a, f)`` states another liveness property (inside a transitive segment constraint), namely that ``a`` amount of Ether is guaranteed to be accessible to contract ``o`` by calling function ``f`` (i.e., ``o`` will definitely receive this amount when calling ``f``, and this cannot be prevented by any other contracts). 

## Other specification constructs
2vyper supports some other specification constructs that are not mentioned directly in the paper. We list some of them here to enable the reader to understand the specified properties where they are used in examples in our evaluation. 

#### Function-specific segment constraints: 
By writing ``check`` before a function instead of ``always check`` on the contract level, one can specify segment constraints that should hold only for the local segments of a specific function.

#### Contractwide postconditions: 
When writing a contract-level specificatio using the keyword ``always ensures`` (similar to the declaration of function constraints, as shown above, but without the ``preserves`` keyword), one can write postconditions that must hold for *every* function in the contract. However, unlike function constraints, these do not have to be transitive, and may not be assumed at any point during verification; they exist only because occasionally, common postconditions must hold for all functions in a contract, and writing them once using a contractwide postcondition is more convenient than writing them separately for every function. 

