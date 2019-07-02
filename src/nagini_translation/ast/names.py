"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

# Constants for names in the original AST

# Decorators
PUBLIC = 'public'
PRIVATE = 'private'
PAYABLE = 'payable'

# Types
BOOL = 'bool'
WEI_VALUE = 'wei_value'
TIMESTAMP = 'timestamp'
TIMEDELTA = 'timedelta'
INT128 = 'int128'
UINT256 = 'uint256'
ADDRESS = 'address'
MAP = 'map'
BYTE = 'bytes'
BYTES32 = 'bytes32'
STRING = 'string'
EVENT = 'event'

# Functions
INIT = '__init__'

# Variables
SELF = 'self'
SELF_BALANCE = 'balance'
MSG = 'msg'
MSG_SENDER = 'sender'
MSG_VALUE = 'value'
MSG_GAS = 'gas'
BLOCK = 'block'
BLOCK_TIMESTAMP = 'timestamp'
LOG = 'log'

# Constants
ZERO_ADDRESS = 'ZERO_ADDRESS'
EMPTY_BYTES32 = 'EMPTY_BYTES32'

CONSTANT_VALUES = {
    ZERO_ADDRESS: '0',
    EMPTY_BYTES32: '"\\x00"' * 32
}

# Special
UNITS = 'units'
INDEXED = 'indexed'
UNREACHABLE = 'UNREACHABLE'

# Ether units
ETHER_UNITS = {
    'wei': 1,
    'kwei': 1_000,
    'babbage': 1_000,
    'mwei': 1_000_000,
    'lovelace': 1_000_000,
    'gwei': 1_000_000_000,
    'shannon': 1_000_000_000,
    'microether': 1_000_000_000_000,
    'szabo': 1_000_000_000_000,
    'milliether': 1_000_000_000_000_000,
    'finney': 1_000_000_000_000_000,
    'ether': 1_000_000_000_000_000_000
}

# Built-in functions
RANGE = 'range'
MIN = 'min'
MAX = 'max'
CLEAR = 'clear'
SEND = 'send'
AS_WEI_VALUE = 'as_wei_value'
AS_UNITLESS_NUMBER = 'as_unitless_number'
LEN = 'len'
CONCAT = 'concat'
KECCAK256 = 'keccak256'
SHA256 = 'sha256'

RAW_CALL = 'raw_call'
RAW_CALL_OUTSIZE = 'outsize'
RAW_CALL_VALUE = 'value'
RAW_CALL_GAS = 'gas'

# Verification
INVARIANT = 'invariant'
GENERAL_POSTCONDITION = 'always_ensures'
GENERAL_CHECK = 'always_check'
PRECONDITION = 'requires'
POSTCONDITION = 'ensures'
CHECK = 'check'

IMPLIES = 'implies'
FORALL = 'forall'
SUCCESS = 'success'
RESULT = 'result'
OLD = 'old'
SUM = 'sum'
SENT = 'sent'
RECEIVED = 'received'
EVENT = 'event'

NOT_ALLOWED_IN_SPEC = [CLEAR, SEND, RANGE]
