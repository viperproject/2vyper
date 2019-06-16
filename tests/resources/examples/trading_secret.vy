
seller: address
buyer: address

price: wei_value

data: bytes[4096]
key_hash: bytes32
key: bytes32

key_confirmed: bool
payed: bool
data_set: bool
data_confirmed: bool

end_time: timestamp


@public
def __init__(_buyer: address, _price: wei_value, _key_hash: bytes32, duration: timedelta):
    self.seller = msg.sender
    self.buyer = _buyer
    self.price = _price
    self.key_hash = _key_hash
    self.end_time = block.timestamp + duration


@public
def confirm_key():
    assert msg.sender == self.buyer
    self.key_confirmed = True


@public
@payable
def pay():
    assert msg.sender == self.buyer
    assert msg.value == self.price
    assert self.key_confirmed
    self.payed = True


@public
def set_data(_data: bytes[4096]):
    assert msg.sender == self.seller
    assert self.payed
    self.data = _data
    self.data_set = True


@public
def confirm_data():
    assert msg.sender == self.buyer
    assert self.data_set
    self.data_confirmed = True


@public
def reject_data(_key: bytes32):
    assert msg.sender == self.buyer
    assert self.data_set
    assert sha256(_key) == self.key_hash
    self.key = _key
    send(msg.sender, self.price)


@public
def withdraw():
    if msg.sender == self.seller:
        assert block.timestamp > self.end_time and self.data_set or self.data_confirmed
    elif msg.sender == self.buyer:
        assert block.timestamp > self.end_time and self.payed and not self.data_set
    else:
        raise "Illegal sender"

    send(msg.sender, self.price)
