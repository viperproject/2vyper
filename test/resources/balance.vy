
money: wei_value


#@ invariant: self.money <= self.balance


#@ ensures: self.balance == old(self.balance)
@public
def get_balance() -> wei_value:
    return self.balance


#@ ensures: self.balance == old(self.balance) + msg.value
@public
@payable
def pay():
    self.money += msg.value