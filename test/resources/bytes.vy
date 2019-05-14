
bb100: bytes[100]


#@ ensures: len(self.bb100) <= 100
@public
def get_bb100() -> bytes[100]:
    return self.bb100

#@ ensures: len(self.bb100) == 3
@public
def set_bb100():
    self.bb100 = b"abc"