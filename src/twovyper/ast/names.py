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

# Modifiers
CONSTANT = 'constant'
MODIFYING = 'modifying'

# Types
BOOL = 'bool'
WEI_VALUE = 'wei_value'
TIMESTAMP = 'timestamp'
TIMEDELTA = 'timedelta'
INT128 = 'int128'
UINT256 = 'uint256'
DECIMAL = 'decimal'
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
BLOCK_COINBASE = 'coinbase'
BLOCK_DIFFICULTY = 'difficulty'
BLOCK_NUMBER = 'number'
BLOCK_PREVHASH = 'prevhash'
BLOCK_TIMESTAMP = 'timestamp'
TX = 'tx'
TX_ORIGIN = 'origin'
LOG = 'log'

# Constants
ZERO_ADDRESS = 'ZERO_ADDRESS'
EMPTY_BYTES32 = 'EMPTY_BYTES32'

CONSTANT_VALUES = {
    ZERO_ADDRESS: '0',
    EMPTY_BYTES32: 'b"' + '\\x00' * 32 + '"'
}

# Special
UNITS = 'units'
IMPLEMENTS = 'implements'
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
FLOOR = 'floor'
CEIL = 'ceil'
CLEAR = 'clear'
SEND = 'send'
AS_WEI_VALUE = 'as_wei_value'
AS_UNITLESS_NUMBER = 'as_unitless_number'
CONVERT = 'convert'
LEN = 'len'
CONCAT = 'concat'
KECCAK256 = 'keccak256'
SHA256 = 'sha256'
ASSERT_MODIFIABLE = 'assert_modifiable'

RAW_CALL = 'raw_call'
RAW_CALL_OUTSIZE = 'outsize'
RAW_CALL_VALUE = 'value'
RAW_CALL_GAS = 'gas'
RAW_CALL_DELEGATE_CALL = 'delegate_call'

# Verification
INVARIANT = 'invariant'
GENERAL_POSTCONDITION = 'always_ensures'
GENERAL_CHECK = 'always_check'
POSTCONDITION = 'ensures'
CHECK = 'check'

CONFIG = 'config'
CONFIG_NO_GAS = 'no_gas'

IMPLIES = 'implies'
FORALL = 'forall'
RESULT = 'result'
OLD = 'old'
ISSUED = 'issued'
SUM = 'sum'
SENT = 'sent'
RECEIVED = 'received'
ACCESSIBLE = 'accessible'
REORDER_INDEPENDENT = 'reorder_independent'
EVENT = 'event'

SUCCESS = 'success'
SUCCESS_IF_NOT = 'if_not'
SUCCESS_OUT_OF_GAS = 'out_of_gas'
SUCCESS_SENDER_FAILED = 'sender_failed'
SUCCESS_CONDITIONS = [SUCCESS_OUT_OF_GAS, SUCCESS_SENDER_FAILED]

NOT_ALLOWED_IN_SPEC = [ASSERT_MODIFIABLE, CLEAR, SEND, RAW_CALL]
NOT_ALLOWED_IN_INVARIANT = [*NOT_ALLOWED_IN_SPEC, SUCCESS, RESULT, ISSUED, REORDER_INDEPENDENT, EVENT]
NOT_ALLOWED_IN_CHECK = [*NOT_ALLOWED_IN_SPEC, ACCESSIBLE, RESULT]
NOT_ALLOWED_IN_POSTCONDITION = [*NOT_ALLOWED_IN_SPEC, ACCESSIBLE, EVENT]
NOT_ALLOWED_IN_TRANSITIVE_POSTCONDITION = [*NOT_ALLOWED_IN_INVARIANT, REORDER_INDEPENDENT, ACCESSIBLE]

# Heuristics
WITHDRAW = 'withdraw'
