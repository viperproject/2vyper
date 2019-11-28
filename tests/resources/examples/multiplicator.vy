# Adapted from https://github.com/crytic/not-so-smart-contracts/blob/ba7edae9e996d7e92f3e3f4651f4e7595d4ef579/honeypots/Multiplicator/Multiplicator.sol
# Example of a honeypot


owner: address


#@ invariant: self.owner == old(self.owner)
# Only the owner ever gets ether
#@ invariant: forall({a: address}, {sent(a)}, a != self.owner ==> sent(a) == 0)


@public
def __init__():
    self.owner = msg.sender


@public
@payable
def withdraw():
    assert msg.sender == self.owner
    send(msg.sender, self.balance)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success() and msg.value >= old(self.balance) ==> sent(msg.sender) >= msg.value
@public
@payable
def multiplicate():
    """
    This function gives the impression that it pays out more ether than was invested, however,
    self.balance implicitly tracks the amount received in msg.value and therefore the if-condition
    is always false (so it never pays out anything).
    """
    if msg.value > self.balance:
        send(msg.sender, self.balance + msg.value)
