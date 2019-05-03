
mp: map(int128, uint256)
mpp: map(int128, map(int128, uint256))

#@ ensures: implies(a == 0, not success())
@public
def div(a: int128):
    self.mp[100 / a] = 12


#@ ensures: implies(a == 0, not success())
@public
def div2(a: int128):
    self.mpp[1 / a][100] = 12


#@ ensures: implies(a == 0, not success())
@public
def div3(a: int128):
    self.mp[1 / a] += 12