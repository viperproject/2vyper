
mp: map(int128, int128)
fld: int128


#@ ensures: self.fld == old(self.fld) + 1
@public
def increment():
    self.fld += 1


@public
def local_increment():
    i: int128
    i += 1


#@ ensures: self.mp[12] == old(self.mp[12]) + 1
@public
def map_increment():
    self.mp[12] += 1


#@ ensures: self.mp[12] == old(self.mp[12]) + self.fld - 12
@public
def increase():
    i: int128
    i += i + 12
    self.mp[i] += self.fld - i