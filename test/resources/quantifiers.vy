
mp: map(int128, int128)


#:: ExpectedOutput(invariant.violated:assertion.false, CH)
#@ invariant: forall({i: int128}, {self.mp[i]}, self.mp[i] == 0)


@public
def no_change():
    pass


@public
def no_change2():
    self.mp[4] = 1
    self.mp[4] = 0


#:: Label(CH)
@public
def change():
    self.mp[0] = 42

