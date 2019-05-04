
mpp: map(int128, map(uint256, int128))
mp: map(address, int128)

fi: int128
ad: address


#@ ensures: self.fi == 0
#@ ensures: self.ad == ZERO_ADDRESS
#@ ensures: self.mp[12] == 0
#@ ensures: self.mpp[10][10000] == 0
@public
def set():
    clear(self.fi)
    clear(self.ad)
    clear(self.mp[12])
    clear(self.mpp)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.fi == 12
@public
def set2():
    self.fi = 12
    clear(self.fi)