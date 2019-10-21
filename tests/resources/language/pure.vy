#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


val: int128


#@ invariant: self.get_val() == self.val
#@ invariant: self._get_val() == self.val
#@ invariant: self._get_val() >= old(self._get_val())

#@ always check: self.get_val() == self.val
#@ always ensures: as_wei_value(self.get_val(), "wei") == self.val


#@ pure
@private
@constant
def _get_val() -> int128:
    return self.val


#@ ensures: implies(success(), result() == self._get_val())
#@ pure
@public
@constant
def get_val() -> int128:
    return self._get_val()


@public
@constant
def get_val_plus(i: int128) -> int128:
    return self.val + 1


#@ ensures: implies(success(), result() == old(self._get_val()))
#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() == self._get_val())
@public
def set_val(new_val: int128) -> int128:
    assert new_val >= self.val

    old_val: int128 = self.val
    self.val = new_val
    return old_val
