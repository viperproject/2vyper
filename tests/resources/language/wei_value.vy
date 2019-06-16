
ui: wei_value
mp: map(int128, wei_value)

#@ ensures: self.ui >= 0
@public
def simple():
    pass

#@ ensures: result() >= 0
@public
def calc() -> wei_value:
    return self.mp[100]

#@ ensures: result() >= 0
@public
def args(arg: wei_value) -> wei_value:
    return arg

#@ ensures: result() >= 0
@public
def add(a: wei_value, b: wei_value) -> wei_value:
    return a + b * a + a * b

#@ ensures: success()
@public
def div(a: wei_value, b: wei_value) -> wei_value:
    return a / (b + 1)

#@ ensures: not success()
@public
def fail(a: wei_value, b: wei_value) -> wei_value:
    assert a > b
    self.ui = b - a

#@ ensures: result() == as_wei_value(i, "lovelace")
@public
def transform(i: int128) -> wei_value:
    return as_wei_value(i, "lovelace")