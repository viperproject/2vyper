
#:: ExpectedOutput(invariant.violated:assertion.false, FF)
#@ invariant: old(self.balance) == self.balance

#:: Label(FF)
@public
def foo():
    pass