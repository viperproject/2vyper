#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

reward: wei_value


@public
@payable
def __init__(_reward: wei_value):
    assert _reward >= msg.value

    self.reward = _reward


@public
def get_reward():
    raw_call(msg.sender, b"", outsize=0, value=self.reward, gas=msg.gas)


@public
def get_reward_out_of_order():
    raw_call(msg.sender, b"", gas=msg.gas, outsize=0, value=self.reward)


@public
def call_with_result(func: bytes[4]):
    res: bytes[4] = raw_call(msg.sender, func, outsize=4, value=self.reward, gas=msg.gas)


@public
def raw_call_no_val(func: bytes[4]):
    res: bytes[128] = raw_call(msg.sender, func, outsize=128, gas=msg.gas)


@private
def with_bytes(b: bytes[12]) -> int128:
    return 5


@public
def raw_call_inline(func: bytes[4]) -> int128:
    return self.with_bytes(raw_call(msg.sender, func, outsize=12, value=self.reward, gas=msg.gas))
