# @version 0.2.11

#
# Copyright (c) 2021 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas, allocation


bb1001: Bytes[100]
bb1002: Bytes[100]


#@ ensures: len(self.bb1001) == 3
#@ ensures: len(self.bb1002) == 1
@external
def set_bb100():
    self.bb1001 = b"abc"
    self.bb1002 = slice(self.bb1001, 1, 1)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: len(self.bb1002) == 2
@external
def set_bb100_fail():
    self.bb1001 = b"abc"
    self.bb1002 = slice(self.bb1001, 1, 1)


#@ ensures: success() == (strt <= 2)
#@ ensures: strt == 1 ==> self.bb1002 == b"b"
@external
def fail_definitely(strt: uint256):
    self.bb1001 = b"abc"
    self.bb1002 = slice(self.bb1001, strt, 1)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: success()
@external
def fail_definitely_fail1(strt: uint256):
    self.bb1001 = b"abc"
    self.bb1002 = slice(self.bb1001, strt, 1)


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: strt == 1 ==> self.bb1002 == b"a"
@external
def fail_definitely_fail2(strt: uint256):
    self.bb1001 = b"abc"
    self.bb1002 = slice(self.bb1001, strt, 1)


