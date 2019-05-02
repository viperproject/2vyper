
mp: map(int128, int128)

#:: ExpectedOutput(invariant.violated:assertion.false)
#@ invariant: old(sum(self.mp)) == sum(self.mp)

#@ ensures: sum(self.mp) == 0
@public
def __init__():
    pass

@public
def change_mp():
    self.mp[12] += 10
    self.mp[13] -= 10

@public
def change_mp_wrong():
    self.mp[42] = 0