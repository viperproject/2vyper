
f: int128


#:: Label(CC)
#@ always ensures: self.f == old(self.f)


@public
def no_change():
    self.f = self.f


#:: ExpectedOutput(postcondition.violated:assertion.false, CC)
@public
def change():
    self.f += 1