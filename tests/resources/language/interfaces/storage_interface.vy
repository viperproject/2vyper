#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from . import interface


i: interface


#@ invariant: self.i == old(self.i)


@public
def __init__():
    self.i = interface(msg.sender)


@public
def get_foo(val: int128) -> int128:
    return self.i.foo(val)