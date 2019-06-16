

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.balance == msg.value
@public
@payable
def __init__():
    pass