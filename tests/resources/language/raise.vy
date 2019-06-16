
#@ ensures: not success()
@public
def test_raise():
    raise "Error"


#@ ensures: implies(a, not success())
@public
def test_raise_conditional(a: bool):
    if a:
        raise "Error"
