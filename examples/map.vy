
mp: map(int128, int128)
i: int128

#@ invariant: self.i == 0
#@ invariant: self.mp[self.i] == 0

@public
def __init__():
    self.i = 20
    self.i = self.mp[self.i]


#@ ensures: self.mp[100] == 8
@public
def write_map():
    self.mp[100] = 8


@public
def write_mult():
    self.mp[self.i] = 10
    self.mp[self.i] = 0


# This should fail
@public
def write_wrong():
    self.mp[self.i] = 42