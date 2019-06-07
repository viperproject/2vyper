
Transfer: event({_from: indexed(address), _to: indexed(address), _value: uint256})


val: int128
ad: address
weis: uint256

ads: address[10]


@public
def transfer(_to: address, _amount: uint256):
    log.Transfer(msg.sender, _to, _amount)


@private
def inc_val() -> address:
    self.val += 1
    return self.ad


#@ ensures: self.val == old(self.val) + 1
@public
def transfer_stmts():
    log.Transfer(msg.sender, self.inc_val(), self.weis)


#@ ensures: not success()
@public
def transfer_not_success(idx: int128):
    assert idx > 10
    log.Transfer(msg.sender, self.ads[idx], self.weis)
