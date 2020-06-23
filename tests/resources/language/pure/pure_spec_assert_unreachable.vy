#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

a: int128
b: int128

#@ pure
@private
@constant
def get_a() -> int128:
    if False:
        assert False, UNREACHABLE
    return self.a

#@ pure
@private
@constant
def get_b() -> int128:
    if False:
        raise UNREACHABLE
    return self.b

#@ pure
@private
@constant
def get_a_fail() -> int128:
    if True:
        #:: ExpectedOutput(assert.failed:assertion.false)
        assert False, UNREACHABLE
    return self.a

#@ pure
@private
@constant
def get_b_fail() -> int128:
    if True:
        #:: ExpectedOutput(assert.failed:assertion.false)
        raise UNREACHABLE
    return self.b

#@ ensures: result(self.get_a()) == self.a
#@ ensures: result(self.get_b()) == self.b
@public
def compliant():
    pass

#:: ExpectedOutput(function.failed:function.revert) | ExpectedOutput(carbon)(postcondition.violated:assertion.false)
#@ ensures: result(self.get_a_fail()) == self.a
@public
def not_compliant_1():
    pass

#:: ExpectedOutput(function.failed:function.revert) | ExpectedOutput(carbon)(postcondition.violated:assertion.false)
#@ ensures: result(self.get_b_fail()) == self.b
@public
def not_compliant_2():
    pass