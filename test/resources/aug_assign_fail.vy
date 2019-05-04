
mp: map(int128, uint256)
f: uint256


#@ ensures: success() == (k <= old(self.f))
@public
def minus(k: uint256):
    self.f -= k


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.f + k == old(self.f)
@public
def minus_fail(k: uint256):
    self.f -= k


#@ ensures: success() == k <= self.f
@public
def map_minus():
    self.mp[12] -= self.f


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.mp[12] + self.f == old(self.mp[12])
@public
def map_minus():
    self.mp[12] -= self.f


#@ ensures: success() == (a != 0)
@public
def div(a: uint256):
    self.f /= a


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success()
@public
def div(a: uint256):
    self.f /= a