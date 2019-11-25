#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ interface


#@ ghost:
    #@ def _value() -> int128: ...


#@ ensures: success() ==> result() == _value(self)
@public
@constant
def get_value() -> int128:
    raise "Not implemented"


#@ ensures: success() ==> _value(self) == new_value
#@ ensures: storage(msg.sender) == old(storage(msg.sender))
@public
def set_value(new_value: int128):
    raise "Not implemented"


#@ ensures: forall({a: address}, {storage(a)}, storage(a) == old(storage(a)))
#@ ensures: storage(msg.sender) == old(storage(msg.sender))   # Needed for Carbon
@public
def change_nothing():
    raise "Not implemented"
