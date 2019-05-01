
mp: map(int128, int128)
mpp: map(int128, map(int128, int128))

i: int128

#@ ensures: self.i == self.mp[12] + 4
@public
def set_i():
    self.i = self.mp[12] + 4

@public
def get_12_13() -> int128:
    return self.mpp[12][13]