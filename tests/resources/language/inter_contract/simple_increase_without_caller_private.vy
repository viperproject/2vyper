#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ interface

#@ ghost:
    #@ def mapping() -> map(address, uint256): ...

# Does not alter mappings of other simple_increase_without_caller_private contracts
#@ always ensures: forall({a: address, b: address}, {mapping(a)[b]}, (a != self and implements(a, simple_increase_without_caller_private)) ==> old(mapping(a)[b]) == mapping(a)[b])

# Does not alter state of other contracts
#@ always ensures: msg.sender != self ==> storage(msg.sender) == old(storage(msg.sender))
#@ always ensures: forall({a: address}, {storage(a)}, a != self ==> storage(a) == old(storage(a)))

#@ invariant: mapping(self)[ZERO_ADDRESS] == 0

#@ ensures: forall({a: address}, {mapping(self)[a]}, a != msg.sender ==> old(mapping(self)[a]) == mapping(self)[a])
#@ ensures: success() ==> old(mapping(self)[msg.sender]) + 1 == mapping(self)[msg.sender]
@public
def increase() -> bool:
    raise "Not implemented"

#@ ensures: success() ==> result() == mapping(self)[msg.sender]
@public
@constant
def get() -> uint256:
    raise "Not implemented"
