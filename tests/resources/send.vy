
money: wei_value


#@ invariant: forall({a: address}, {sent(a), old(sent(a))}, old(sent(a)) <= sent(a))
#:: Label(MM)
#@ invariant: self.money <= self.balance


#@ ensures: implies(not success(), self.balance == old(self.balance))
@public
def send_balance(to: address):
    self.money = 0
    send(to, self.money)


@public
def send_balance_fail(to: address):
    #:: ExpectedOutput(call.invariant:assertion.false, MM)
    send(to, self.money)
    self.money = 0