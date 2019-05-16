
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