#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: success() ==> result() != ZERO_ADDRESS
#@ ensures: success() ==> sent(at) == old(sent(at))
@public
def create_new(at: address) -> address:
    return create_forwarder_to(at)


#@ ensures: success() ==> result() != ZERO_ADDRESS
#@ ensures: success() ==> sent(at) == old(sent(at)) + msg.value
@public
@payable
def create_new_with_value(at: address) -> address:
    new: address = create_forwarder_to(at, value=msg.value)
    assert new.balance == msg.value
    return new
