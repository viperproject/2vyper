# Allocation

## Model

Three maps are used to model the allocation of resources.

- <a name="offer_map"></a>**Offered Map**:
  - Type: _Map[Resource, Map[Resource, Map[Offer, Int]]]_
  - Offered map tracks for each resource trade (resource from / to) all current offers.
  - An offer is a four-tuple of integers. (amount of first resource, amount of second resource, address of provider of first resource, address of provider of second resource)
  - The last integer is the number of such offers.

- <a name="trust_map"></a>**Trusted Map**:
  - Type: _Map[Address, Map[Address, Bool]]_
  - This maps stores which other addresses an address trusts (besides itself).
  - Meaning: The first address trusts the second address if the value is `True`.

- <a name="allocated_map"></a>**Allocated Map**:
  - Type: _Map[Resource, Map[Address, Int]]_
  - The given address has that many times such a resource.
  - E.g. Payable functions change this allocated map. It allocates the sent Ether to the `msg.sender`. 

## Special Resources

- <a name="wei_resource"></a>**Wei**:
  - The resource for Ether / Wei is implicitly given and must not be declared.
  - It is the default resource if no other recource is provided.

- <a name="creator_resource"></a>**Creator**:
  - Type: _Resource{$resource: Resource}_
  - Only the initializer function (init) is allowed to create other resources unchecked.
  - If a resource is created outside of init, a creater resource is needed.
  - For [create](#create_fun) and [destroy](#destroy_fun), it gets checked that an address has the creator resource of the wanted resource.

## Further information

Sending and receiving Ether using send or calls is handled. Also, if `selfdestruct` gets called a check is made that the receiver of the remaining Ether has access to the whole balance and cannot not _steal_ Ether of other addresses.


## Recource functions

- <a name="trust_fun"></a>**trust**:
  - Signature: trust\(_target\_address_, _do\_trust_, acting_for=_source\_address_\)
    - The `acting_for` keyword argument can be omitted. It will default to the `msg.sender`.
  - Update the [trust map](#trust_map).
    - Check that the source address is trusted.
    - Change the trusted flag according to `do_trust` for the given target and source address.

- <a name="offer_fun"></a>**offer**:
  - Signature: offer\[_offered\_resource_ <-> _wanted\_resource_\]\(_offered\_amount_, _wanted\_amount_, to=_target\_address_, times=_number\_of_offers_, acting_for=_source\_address_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between [wei resources](#wei_resource).
    - The `acting_for` keyword argument can be omitted. It will default to the `msg.sender`.
  - Enable a possible exchange between resources.
    - Check that the source address is trusted.
    - Add number of such an offer in the [offer map](#offer_map) with the provided number of times.

- <a name="revoke_fun"></a>**revoke**:
  - Signature: revoke\[_offered\_resource_ <-> _wanted\_resource_\]\(_offered\_amount_, _wanted\_amount_, to=_target\_address_, acting_for=_source\_address_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between [wei resources](#wei_resource).
    - The `acting_for` keyword argument can be omitted. It will default to the `msg.sender`.
  - Revoke all such offerings.
    - Check that the source address is trusted.
    - Change number of such an offer in the [offer map](#offer_map) to zero.

- <a name="exchange_fun"></a>**exchange**:
  - Signature: exchange\[_first\_resource_ <-> _second\_resource_\]\(_amount\_of_first_resource_, _amount\_of_second_resource_, _address\_of_first_provider_, _address\_of_second_provider_, times=_number\_of_exchanges_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between [wei resources](#wei_resource).
  - Exchanges first resource with the second resource with the specified providers and amounts.
    - Check that the first provider either does not need to provide anything or else has made such an offering.
    - Check that the second provider either does not need to provide anything or else has made such an offering.
    - If any offers are needed remove them.
    - Check that the first provider has enogh resources allocated.
    - Check that the second provider has enogh resources allocated.
    - Decrease allocated amount of the first resource for the first provider.
    - Increase allocated amount of the second resource for the first provider.
    - Decrease allocated amount of the second resource for the second provider.
    - Increase allocated amount of the first resource for the second provider.

- <a name="reallocate_fun"></a>**reallocate**:
  - Signature: reallocate\[_resource_\]\(_amount_, to=_target\_address_, acting_for=_source\_address_\)
    - The square bracket with the resource can be omitted. It will then default to the [wei resource](#wei_resource).
    - The `acting_for` keyword argument can be omitted. It will default to the `msg.sender`.
  - A given amount of a resource will be handed over to another address.
    - Check that the source address is trusted.
    - Check that the source address has enough resources allocated.
    - Decrease allocated amount of the resource for the source address.
    - Increase allocated amount of the resource for the target address.
  - A reallocate is equivalent to an offer followed by an exchange. E.g.
    This reallocate is equivalent to\.\.\.
    ```
    #@ reallocate[token](amount, to=to, acting_for=self.minter)
    ```
    \.\.\. this offer exchange pair.
    ```
    #@ offer[token <-> token](amount, 0, acting_for=self.minter, to=to, times=1)
    #@ exchange[token <-> token](amount, 0, self.minter, to, times=1)
    ```

- <a name="create_fun"></a>**create**:
  - Signature: exchange\[_resource_\]\(_amount_, to=_target\_address_, acting_for=_source\_address_\)
    - The `to` keyword argument can be omitted. It will default to the `msg.sender`.
    - The `acting_for` keyword argument can be omitted. It will default to the `msg.sender`.
  - Creates a specified resource a certain amount of times and allocates it to the target address.
    - The init function is allowed to create any resource.
    - If it is not the init function, check that the source address is trusted.
    - If it is not the init function, check that the source address has a [creator resource](#creator_resource) for this resource.
    - Increase allocated amount of the resource for the target address.
  - The [wei resource](#wei_resource) cannot get created.

- <a name="destroy_fun"></a>**destroy**:
  - Signature: destroy\[_resource_\]\(_amount_, acting_for=_address_\)
    - The `acting_for` keyword argument can be omitted. It will default to the `msg.sender`.
  - Destroys a specified resource a certain amount of times.
    - Check that the address is trusted.
    - Check that the address has enogh resources allocated.
    - Decrease allocated amount of the resource for the address.
  - The [wei resource](#wei_resource) cannot get destroyed.

- **foreach**:
  - Signature: foreach\(_dict_, \*_trigger_, _body_\)
    - The `dict` represents the quantified variables with their types, e.g. `{a: address, v: uint256}`
    - Zero or more triggers can be provided. A trigger is a set of expressions that uses all quantified variables. (For more information please consider reading [this](http://viper.ethz.ch/tutorial/?section=#quantifiers))
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
  - Signature: offered\[_offered\_resource_ <-> _wanted\_resource_\]\(_offered\_amount_, _wanted\_amount_, _source\_address_, _target\_address_\)
    - The square bracket with the resources can be omitted. It will then default to an exchange between [wei resources](#wei_resource).
  - The number of offers with these parameters is returned.


- **trusted**:
  - Signature: trusted\(_target\_address_, by=_source\_address_\)
  - Returns wheter the source address trusts the target address.



