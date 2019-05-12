
current_sender: address

#:: Label(OO)|ExpectedOutput(invariant.violated:assertion.false)
#@ invariant: msg.sender == old(msg.sender)
#@ invariant: self.current_sender == msg.sender
#@ invariant: self.current_sender == old(self.current_sender)


#@ ensures: msg.sender == old(msg.sender)
@public
def __init__():
    self.current_sender = msg.sender


#:: ExpectedOutput(invariant.violated:assertion.false, OO)
@public
def set_sender():
    self.current_sender = msg.sender