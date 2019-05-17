
current_sender: address


#@ always ensures: msg.sender == old(msg.sender)
#@ always ensures: self.current_sender == msg.sender
#:: Label(OO)
#@ always ensures: self.current_sender == old(self.current_sender)


#@ ensures: msg.sender == old(msg.sender)
@public
def __init__():
    self.current_sender = msg.sender


#:: ExpectedOutput(postcondition.violated:assertion.false, OO)
@public
def set_sender():
    self.current_sender = msg.sender