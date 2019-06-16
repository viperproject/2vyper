#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

f: int128


#:: ExpectedOutput(invariant.not.wellformed:division.by.zero)
#@ invariant: 1 / self.f == 1


@public
def __init__():
    pass


@public
def send_money():
    send(msg.sender, self.balance)