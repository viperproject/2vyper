
counter: int128


#@ invariant: self.counter <= old(self.counter)


@public
def dec():
    old_counter: int128 = self.counter
    send(ZERO_ADDRESS, as_wei_value(1, "wei"))
    self.counter = old_counter - 1
