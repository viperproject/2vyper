# Allocation

The resource handling per default disabled. It can be enabled using the `allocation` configuration.

## Model

Three maps are used to model the allocation of resources.

- <a name="offer_map"></a>**Offered Map**:
  - Type: _Map[Resource[Address], Map[Resource[Address], Map[Offer, Int]]]_
  - Offered map tracks for each resource trade (resource from / to) all current offers.
  - An offer is a four-tuple of integers. (amount of first resource, amount of second resource, address of provider of
    first resource, address of provider of second resource)
  - A resource is associated with an address and has potentially further arguments.
  - The last integer is the number of such offers.

- <a name="trust_map"></a>**Trusted Map**:
  - Type: _Map[Address, Map[Address, Map[Address, Bool]]]_
  - Where (Address) -> Whom (Address) -> Who (Address) -> Bool
  - This maps stores where, which other addresses an address trusts (besides itself).
  - Meaning: The second address trusts the first address if the value is `True`.

- <a name="allocated_map"></a>**Allocated Map**:
  - Type: _Map[Resource[Address], Map[Address, Int]]_
  - The given address has that many times such a resource.
  - E.g. Payable functions change this allocated map. It allocates the sent Ether to the `msg.sender`. 
  
## Resources

- Normal Resources Declaration:
  ```
  #@ resource: token(id: uint256)
  ```
  A resource has a name and can have any number of arguments (in the example above `id`).

- Derived Resources Declaration:
  ```
  from . import interface
  
  i: interface
  
  #@ resource: token(id: uint256) -> interface.token[self.i]
  ```
  A derived resource has also a name and must have the same arguments as its underlying resource
  (in the example above `id`).
  The underlying resource is specified with its name and an address.
  
  A derived resource corresponds to the right to get the underlying resource.

- Resource Usage:
  ```
  from . import interface
  
  i: interface
  
  #@ reallocate[token[self.i]](...)
  ```
  The resource can be used in the resource functions. To specify which contract has the resource, after each resource 
  a square bracket can be placed, and so the address can be specified. This square bracket can be omitted. The address
  will then default to `self`.


## Special Resources

- <a name="wei_underlying_resource"></a>**Wei**:
  - The resource for Ether / Wei is implicitly given and must not be declared.

- <a name="wei_resource"></a>**wei**:
  - This is the derived resource of [Wei](#wei_underlying_resource). It represents that right to get Wei.
  - It is the default resource if no other resource is provided.

- <a name="creator_resource"></a>**creator**:
  - Type: _Resource[Address]{$resource: Resource[Address]}_
  - Only the initializer function (init) is allowed to create other resources unchecked.
  - If a resource is created outside of init, a creator resource is needed.
  - For [create](#create_fun), it gets checked that an address has the creator resource of the wanted resource.

## Further information

Sending and receiving Ether using send or calls is handled.
Also, if `selfdestruct` gets called a check is made that the receiver of the remaining Ether has access to the whole
balance and cannot not _steal_ Ether of other addresses.

Not only for wei but sending and receiving of any derived resource is handled.
A call is considered sending some derived resource if `self` is the source address.
A call is considered receiving some derived resource if `self` is the target address.


## Resource functions

Each of the following functions (except [exchange](#exchange_fun)) are only allowed if the operation was declared in 
the specification of the function.
E.g. the trust performed in the function foo is only allowed if it was also declared outside the function.
```
#@ performs: trust(a, True)
@public
def foo(a: address):
    # [Some code of foo]
    #@ trust(a, True)
    # [Some further code of foo]
```

These checks can be disabled using the `no_performs` configuration.

- <a name="trust_fun"></a>**trust**:
  - Signature: trust\(_target\_address_, _do\_trust_\)
  - Update the [trust map](#trust_map).
    - Change the trusted flag according to `do_trust` for the given target and source address.

- <a name="offer_fun"></a>**offer**:
  - Signature: offer\[_offered\_resource_ <-> _wanted\_resource_\]\(_offered\_amount_, _wanted\_amount_,
    to=_target\_address_, times=_number\_of_offers_, actor=_source\_address_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between
      [wei resources](#wei_resource).
    - The `actor` keyword argument can be omitted. It will default to the `msg.sender`.
  - Enable a possible exchange between resources.
    - Check that the source address is trusted if the offered amount and times are non-zero.
    - Add number of such an offer in the [offer map](#offer_map) with the provided number of times.

- <a name="revoke_fun"></a>**revoke**:
  - Signature: revoke\[_offered\_resource_ <-> _wanted\_resource_\]\(_offered\_amount_, _wanted\_amount_,
    to=_target\_address_, actor=_source\_address_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between
      [wei resources](#wei_resource).
    - The `actor` keyword argument can be omitted. It will default to the `msg.sender`.
  - Revoke all such offerings.
    - Check that the source address is trusted if the offered amount is non-zero.
    - Change number of such an offer in the [offer map](#offer_map) to zero.

- <a name="allow_to_decompose_fun"></a>**allow_to_decompose**:
  - Signature: allow_to_decompose\[_resource_\]\(_amount_, _address_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between
      [wei resources](#wei_resource)
    - The `resource` must be a derived resource.
  - An address allows to convert its `amount` many derived resources to convert back into its underlying resource.
    - Check that the source address is trusted if the amount is non-zero.
    - Set the number of such an offer in the [offer map](#offer_map) to `amount`.

- <a name="exchange_fun"></a>**exchange**:
  - Signature: exchange\[_first\_resource_ <-> _second\_resource_\]\(_amount\_of_first_resource_,
  _amount\_of_second_resource_, _address\_of_first_provider_, _address\_of_second_provider_,
      times=_number\_of_exchanges_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between
      [wei resources](#wei_resource).
  - Exchanges first resource with the second resource with the specified providers and amounts.
    - Check that the first provider either does not need to provide anything or else has made such an offering.
    - Check that the second provider either does not need to provide anything or else has made such an offering.
    - If any offers are needed, remove them.
    - Check that the first provider has enough resources allocated.
    - Check that the second provider has enough resources allocated.
    - Decrease allocated amount of the first resource for the first provider.
    - Increase allocated amount of the second resource for the first provider.
    - Decrease allocated amount of the second resource for the second provider.
    - Increase allocated amount of the first resource for the second provider.

- <a name="reallocate_fun"></a>**reallocate**:
  - Signature: reallocate\[_resource_\]\(_amount_, to=_target\_address_, actor=_source\_address_\)
    - The square bracket with the resource can be omitted. It will then default to the [wei resource](#wei_resource).
    - The `actor` keyword argument can be omitted. It will default to the `msg.sender`.
  - A given amount of a resource will be handed over to another address.
    - Check that the source address is trusted if the amount is non-zero.
    - Check that the source address has enough resources allocated.
    - Decrease allocated amount of the resource for the source address.
    - Increase allocated amount of the resource for the target address.
  - A `reallocate` is equivalent to an offer followed by an exchange. E.g.
    This `reallocate` is equivalent to\.\.\.
    ```
    #@ reallocate[token](amount, to=to, actor=self.minter)
    ```
    ... this offer exchange pair.
    ```
    #@ offer[token <-> token](amount, 0, actor=self.minter, to=to, times=1)
    #@ exchange[token <-> token](amount, 0, self.minter, to, times=1)
    ```

- <a name="create_fun"></a>**create**:
  - Signature: create\[_resource_\]\(_amount_, to=_target\_address_, actor=_source\_address_\)
    - The `to` keyword argument can be omitted. It will default to the `msg.sender`.
    - The `actor` keyword argument can be omitted. It will default to the `msg.sender`.
    - The `resource` must not be a derived resource.
  - Creates a specified resource a certain amount of times and allocates it to the target address.
    - The init function is allowed to create any normal resource.
    - If it is not the init function, check that the source address is trusted if the amount is non-zero.
    - If it is not the init function, check that the source address has a [creator resource](#creator_resource)
      for this resource.
    - Increase allocated amount of the resource for the target address.

- <a name="destroy_fun"></a>**destroy**:
  - Signature: destroy\[_resource_\]\(_amount_, actor=_address_\)
    - The `actor` keyword argument can be omitted. It will default to the `msg.sender`.
    - The `resource` must not be a derived resource.
  - Destroys a specified resource a certain amount of times.
    - Check that the address is trusted if the amount is non-zero.
    - Check that the address has enough resources allocated.
    - Decrease allocated amount of the resource for the address.
  
- <a name="payable_fun"></a>**payable**:
  - Signature: payable\[_resource_\]\(_amount_\)
    - The square bracket with the resource can be omitted. It will then default to the [wei resource](#wei_resource).
    - The `resource` must be a derived resource.
  - Creates a specified derived resource a certain amount of times and allocates it to the target address if that
    `amount` underlying resource gets allocated to `self`.
    - Increase allocated amount of the resource for the target address.

- <a name="payout_fun"></a>**payout**:
  - Signature: payout\[_resource_\]\(_amount_, actor=_address_\)
    - The square bracket with the resource can be omitted. It will then default to the [wei resource](#wei_resource).
    - The `actor` keyword argument can be omitted. It will default to the `msg.sender`.
    - The `resource` must be a derived resource.
  - Destroys a specified resource a certain amount of times and deallocates it from the target address if that
    `amount` underlying resource gets deallocated from `self`.
    - Decrease allocated amount of the resource for the address.
  
- **allocate untracked wei**:
  - Signature: allocate_untracked_wei\(_address_\)
  - There might be a difference in the sum of the tracked [wei resource](#wei_resource) and the balance of the contract.
  This is due to e.g. coinbase transactions where a contract forcefully gets some Ether without executing any code.
  Using this function, this difference can be allocated to an address.

- **foreach**:
  - Signature: foreach\(_dict_, \*_trigger_, _body_\)
    - The `dict` represents the quantified variables with their types, e.g. `{a: address, v: uint256}`
    - Zero or more triggers can be provided. A trigger is a set of expressions that uses all quantified variables.
      (For more information please consider reading [this](http://viper.ethz.ch/tutorial/?section=#quantifiers))
    - The body has to be one of the following function calls.
      - [offer](#offer_fun)
      - [revoke](#revoke_fun)
      - [create](#create_fun)
      - [destroy](#destroy_fun)
      - [trust](#trust_fun)


## Specification functions

- **allocated**:
  - Signature: allocated\[_resource_\]\(_address_\)
    - The square bracket with the resource can be omitted. It will then default to the [wei resource](#wei_resource).
    - The `address` argument is optional.
  - If no address is provided, the whole [allocated map](#allocated_map) is returned.
  - If an address is provided, the allocated quantity of the given resource for this address is returned.

- **offered**:
  - Signature: offered\[_offered\_resource_ <-> _wanted\_resource_\]\(_offered\_amount_, _wanted\_amount_,
    _source\_address_, _target\_address_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between
      [wei resources](#wei_resource).
  - The number of offers with these parameters is returned.

- **no_offers**:
  - Signature: no_offers\[_offered\_resource_\]\(_source\_address_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between
      [wei resources](#wei_resource).
  - Returns `True` when the `source_address` has no open offers of the `offered_resource`.

- **trusted**:
  - Signature: trusted\(_target\_address_, by=_source\_address_, where=_location\_address_\)
    - The `where` keyword argument can be omitted. It will default to the `self` address.
  - Returns whether the source address trusts the target address.

- **trust_no_one**:
  - Signature: trust_no_one\(_address_, _location\_address_\)
  - Returns `True` iff the address does not trust anyone at the location address.

- **allowed_to_decompose**:
  - Signature: allowed_to_decompose\[_resource_\]\(_address_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between
      [wei resources](#wei_resource).
  - Returns the amount of the derived resource `resource` that is allowed to get decomposed by `address`.



