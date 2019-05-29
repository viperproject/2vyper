
f: int128


#:: ExpectedOutput(invariant.not.wellformed:division.by.zero)
#@ invariant: 1 / self.f == 1


@public
def __init__():
    pass


@public
def send_money():
    send(msg.sender, self.balance)