#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ ensures: implies(success(), result() == 
#@     b'\x00\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x00\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90')
@public
def use_byte_literal() -> bytes32:
    return 0x0012345678901234567890123456789000123456789012345678901234567890


#@ ensures: implies(success(), result() == EMPTY_BYTES32)
@public
def use_byte_literal_zero() -> bytes32:
    return 0x0000000000000000000000000000000000000000000000000000000000000000
