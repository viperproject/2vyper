# step 1
#@ config: allocation


#step 2 and 10 (allowed to liquidate
#@ invariant: ((self.state == BET_PLACED and self.guess == (convert(keccak256_inv(self.hashedNumber), uint256) % 2 == 0)) ==>
#@             (allocated(self.operator) == self.pot and allocated(self.player) == self.bet and allowed_to_liquidate[wei](self.player) >= (2 * self.bet)))
#@ invariant: (not (self.state == BET_PLACED and self.guess == (convert(keccak256_inv(self.hashedNumber), uint256) % 2 == 0)) ==>
#@             (allocated(self.operator) == self.pot + self.bet and allocated(self.player) == 0))
#@ invariant: forall({a: address}, {allocated(a)}, a != self.operator and a != self.player ==> allocated(a) == 0)

# step 3
#@ invariant: self.player != self.operator

# step 6:
#@ invariant: self.state != BET_PLACED ==> self.bet == 0

# step 8:
#@ invariant: self.bet <= self.pot

# step 13:
#@ invariant: self.state == IDLE or self.state == GAME_AVAILABLE or self.state == BET_PLACED
#@ invariant: self.operator == old(self.operator)

#@ always check: old(self.state) == IDLE ==> (self.state == IDLE or (self.state == GAME_AVAILABLE and msg.sender == self.operator))
#@ always check: old(self.state) == GAME_AVAILABLE ==> ((self.state == BET_PLACED and msg.sender == self.player and self.hashedNumber == old(self.hashedNumber)) or
#@                                                      (self.state == GAME_AVAILABLE and self.hashedNumber == old(self.hashedNumber)))
#@ always check: old(self.state) == BET_PLACED ==> ((self.state == BET_PLACED and self.guess == old(self.guess) and self.hashedNumber == old(self.hashedNumber)) or
#@                                                  (self.state == IDLE and msg.sender == self.operator))


operator: public(address)  

pot: public(wei_value)

hashedNumber: public(bytes32)

player: public(address)

guess: bool

bet: wei_value

IDLE: constant(int128) = 0
GAME_AVAILABLE: constant(int128) = 1
BET_PLACED: constant(int128) = 2

state: int128

@public
def __init__():
    self.operator = msg.sender
    self.state = IDLE
    self.pot = 0
    self.bet = 0

#@ performs: payable[wei](msg.value)
@public
@payable
def addToPot():
    assert msg.sender == self.operator
    self.pot = self.pot + msg.value


#@ performs: payout[wei](amount)
@public
def removeFromPot(amount: uint256):
    assert self.state != BET_PLACED
    assert msg.sender == self.operator
    self.pot = self.pot - amount # step 4: moved from below send
    send(self.operator, amount)  # possible bug


@public
def createGame(_hashedNumber: bytes32):
    assert self.state == IDLE
    assert msg.sender == self.operator

    self.hashedNumber = _hashedNumber
    self.state = GAME_AVAILABLE

#@ performs: payable[wei](msg.value)
#@ performs: reallocate(msg.value if (_guess != (convert(keccak256_inv(self.hashedNumber), uint256) % 2 == 0)) else 0, to=self.operator)
#@ performs: allow_to_liquidate[wei](2 * msg.value if (_guess == (convert(keccak256_inv(self.hashedNumber), uint256) % 2 == 0)) else 0, msg.sender)
@public
@payable
def placeBet(_guess: bool):
    assert self.state == GAME_AVAILABLE
    assert msg.sender != self.operator
    assert msg.value <= self.pot

    self.state = BET_PLACED
    self.player = msg.sender

    self.bet = msg.value
    self.guess = _guess

    # step 5
    #@ if _guess != (convert(keccak256_inv(self.hashedNumber), uint256) % 2 == 0):
        #@ reallocate(msg.value, to=self.operator)
    #@ else:
        #@ allow_to_liquidate[wei](2 * msg.value, msg.sender)  # step 10


#@ performs: reallocate(self.bet if (self.guess == (secretNumber % 2 == 0)) else 0, to=self.player)
#@ performs: payout[wei](2 * self.bet if (self.guess == (secretNumber % 2 == 0)) else 0, actor=self.player)
@public
def decideBet(secretNumber: uint256):
    assert self.state == BET_PLACED
    assert msg.sender == self.operator
    assert self.hashedNumber == keccak256(convert(secretNumber, bytes32))

    secret: bool = secretNumber % 2 == 0

    self.state = IDLE  # step 12

    if secret == self.guess:
        # step 9
        #@ assert self.guess == (convert(keccak256_inv(self.hashedNumber), uint256) % 2 == 0), UNREACHABLE
        # step 7
        #@ reallocate(self.bet, to=self.player)
        self.pot = self.pot - self.bet

        tmp: wei_value = self.bet  # moved and introd, step 11
        self.bet = 0

        send(self.player, 2 * tmp)  # likely bug
        # self.bet = 0  # moved (step 11
    else:
        self.pot = self.pot + self.bet
        self.bet = 0

    # self.state = IDLE # moved, step 12
