
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result()
@public
def func() -> bool:
    return False

#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success()
def func2():
    assert False