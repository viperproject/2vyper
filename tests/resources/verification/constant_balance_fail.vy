
#:: Label(CONST_BALANCE)
#@ invariant: old(self.balance) == self.balance

#:: ExpectedOutput(invariant.violated:assertion.false, CONST_BALANCE)
@public
def foo():
    pass