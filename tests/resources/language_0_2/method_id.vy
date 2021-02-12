# @version 0.2.x

#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

@external
@view
def foo() -> Bytes[4]:
    return method_id('transfer(address,uint256)')

@external
@view
def bar() -> Bytes[4]:
    return method_id('transfer(address,uint256)', output_type=Bytes[4])

@external
@view
def baz() -> bytes32:
    return method_id('transfer(address,uint256)', output_type=bytes32)
