
bts: bytes[1024]


#@ ensures: len(self.bts) == 2 * len(b)
@public
def double(b: bytes[512]):
    self.bts = concat(b, b)


#@ ensures: len(self.bts) == 4 * len(b)
@public
def times4(b: bytes[1]):
    self.bts = concat(b, b, b, b)


#@ ensures: result() == concat(b, b, b, b, b)
@public
def times5(b: bytes[1]) -> bytes[5]:
    return concat(b, b, b, b, b)
