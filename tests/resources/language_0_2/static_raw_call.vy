# @version 0.2.x

#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

s: int128

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.s == old(self.s)
@external
@payable
def foo(_target: address) -> Bytes[32]:
    response: Bytes[32] = raw_call(_target, 0xa9059cbb, max_outsize=32, value=msg.value, is_static_call=False)
    return response

#@ ensures: self.s == old(self.s)
@external
def bar(_target: address) -> Bytes[32]:
    response: Bytes[32] = raw_call(_target, 0xa9059cbb, max_outsize=32, is_static_call=True)
    return response
