#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

struct MyStruct:
    value1: int128
    value2: decimal

#@pure
@private
@constant
def test_bool() -> bool:
    return False

#@pure
@private
@constant
def test_int128() -> int128:
    return 0

#@pure
@private
@constant
def test_uint256() -> uint256:
    return 1361129467683753853853498429727072845824

#@pure
@private
@constant
def test_decimal() -> decimal:
    return 42.0

#@pure
@private
@constant
def test_address() -> address:
    return 0x000000001000000000010000000000000600000a

#@pure
@private
@constant
def test_bytes32() -> bytes32:
    return 0x0000000000000000000000000000000000000000000000000000000080ac58cd

#@pure
@private
@constant
def test_bytes() -> bytes[3]:
    return b"\x01\x02\x03"

#@pure
@private
@constant
def test_string() -> string[100]:
    return "Test String"

#@pure
@private
@constant
def test_list() -> int128[3]:
    return [1, 2, 3]

#@pure
@private
@constant
def test_struct() -> MyStruct:
    return MyStruct({value1: 1, value2: 2.0})


#@ ensures: result(self.test_bool()) == False
#@ ensures: result(self.test_int128()) == 0
#@ ensures: result(self.test_uint256()) == 1361129467683753853853498429727072845824
#@ ensures: result(self.test_decimal()) == 42.0
#@ ensures: result(self.test_address()) == 0x000000001000000000010000000000000600000a
#@ ensures: result(self.test_bytes32()) == 0x0000000000000000000000000000000000000000000000000000000080ac58cd
#@ ensures: result(self.test_bytes()) == b"\x01\x02\x03"
#@ ensures: result(self.test_string()) == "Test String"
#@ ensures: result(self.test_list()) == [1, 2, 3]
#@ ensures: result(self.test_struct()) == MyStruct({value1: 1, value2: 2.0})
@public
def test(i: int128):
    pass
