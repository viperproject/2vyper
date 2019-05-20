
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: self.balance == as_wei_value(0, "wei")
@public
def __init__():
    pass