
counter: int128

#@ invariant: self.counter <= old(self.counter)

#@ ensures: implies(success(), self.counter <= old(self.counter) - 2)
@public
def incr():
    self.counter -= 2
    send(ZERO_ADDRESS, as_wei_value(5, "wei"))