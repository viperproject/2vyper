#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# A finite state machine modeling an elevator
# The elevator has two floors (Up, Down) with a light each: red for Ground, green for First


owner: address
fee: wei_value

down: bool
up: bool
red: bool
green: bool


#@ invariant: self.down or self.up and not (self.down and self.up)
#@ invariant: implies(self.up, self.green and not self.red)
#@ invariant: implies(self.down, self.red and not self.green)

#@ always check: implies(self.up and not old(self.up), self.balance == old(self.balance) + self.fee)


@public
def __init__(_fee: wei_value):
    self.owner = msg.sender
    self.fee = _fee
    # We start down
    self.down = True
    self.up = False
    self.red = True
    self.green = False

@private
def go_up():
    self.up = True
    self.down = False
    self.red = False
    self.green = True


@private
def go_down():
    self.up = False
    self.down = True
    self.red = True
    self.green = False


@public
@payable
def call_elevator(flr: uint256):
    assert msg.value == self.fee
    assert flr == 0 or flr == 1

    is_down: bool = self.down
    is_up: bool = self.up

    if flr == 0:
        self.go_down()
    elif flr == 1:
        self.go_up()
    
    if (is_down and self.down) or (is_up and self.up):
        send(msg.sender, msg.value / 2)


@public
def collect_fees():
    assert msg.sender == self.owner
    send(msg.sender, self.balance)
