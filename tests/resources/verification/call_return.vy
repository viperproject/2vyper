#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract C:
    def getu() -> uint256: constant
    def geta() -> bytes[100]: constant
    def geti() -> int128: constant


c: C


@public
def __init__():
    self.c = C(msg.sender)


#@ ensures: implies(success(), result() >= 0)
@public
def checku() -> uint256:
    return self.c.getu()


#@ ensures: implies(success(), 0 <= len(result()) and len(result()) <= 100)
@public
def checka() -> bytes[100]:
    return self.c.geta()


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: implies(success(), result() >= 0)
@public
def checki() -> int128:
    return self.c.geti()


#@ ensures: implies(success(), 0 <= len(result()) and len(result()) <= 100)
@public
def checkr() -> bytes[100]:
    return raw_call(msg.sender, b"", outsize=100, gas=msg.gas)
