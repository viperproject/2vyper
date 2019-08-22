#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


contract C:
    def f(): modifying


time_map: map(timestamp, int128)


#@ transitive:
    #:: Label(TS)
    #@ always ensures: self.time_map[block.timestamp] >= old(self.time_map[block.timestamp])


@public
def __init__():
    pass


@public
def test0():
    self.time_map[block.timestamp] += 5
    C(msg.sender).f()


@public
def test1():
    C(msg.sender).f()


#:: ExpectedOutput(postcondition.violated:assertion.false, TS)
@public
def test_fail():
    self.time_map[block.timestamp] = 5
