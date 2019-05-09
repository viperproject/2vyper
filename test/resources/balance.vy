
#@ ensures: self.balance == old(self.balance)
@public
def get_balance() -> wei_value:
    return self.balance