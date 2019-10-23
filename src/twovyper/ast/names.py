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
INT128 = 'int128'
UINT256 = 'uint256'
DECIMAL = 'decimal'
WEI_VALUE = 'wei_value'
TIMESTAMP = 'timestamp'
TIMEDELTA = 'timedelta'
ADDRESS = 'address'
BYTE = 'bytes'
BYTES32 = 'bytes32'
STRING = 'string'
MAP = 'map'
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
EMPTY_BYTES32 = 'EMPTY_BYTES32'
ZERO_ADDRESS = 'ZERO_ADDRESS'
ZERO_WEI = 'ZERO_WEI'
MIN_INT128 = 'MIN_INT128'
MAX_INT128 = 'MAX_INT128'
MAX_UINT256 = 'MAX_UINT256'
MIN_DECIMAL = 'MIN_DECIMAL'
MAX_DECIMAL = 'MAX_DECIMAL'

CONSTANT_VALUES = {
    EMPTY_BYTES32: 'b"' + '\\x00' * 32 + '"',
    ZERO_ADDRESS: '0',
    ZERO_WEI: '0',
    MIN_INT128: f'-{2 ** 127}',
    MAX_INT128: f'{2 ** 127 - 1}',
    MAX_UINT256: f'{2 ** 256 - 1}',
    MIN_DECIMAL: f'-{2 ** 127}.0',
    MAX_DECIMAL: f'{2 ** 127 - 1}.0'
}

# Special
UNITS = 'units'
IMPLEMENTS = 'implements'
INDEXED = 'indexed'
UNREACHABLE = 'UNREACHABLE'

# Ether units
ETHER_UNITS = {
    ('wei'): 1,
    ('femtoether', 'kwei', 'babbage'): 10 ** 3,
    ('picoether', 'mwei', 'lovelace'): 10 ** 6,
    ('nanoether', 'gwei', 'shannon'): 10 ** 9,
    ('microether', 'szabo'): 10 ** 12,
    ('milliether', 'finney'): 10 ** 15,
    ('ether'): 10 ** 18,
    ('kether', 'grand'): 10 ** 21
}

# Built-in functions
MIN = 'min'
MAX = 'max'
SQRT = 'sqrt'
FLOOR = 'floor'
CEIL = 'ceil'

AS_WEI_VALUE = 'as_wei_value'
AS_UNITLESS_NUMBER = 'as_unitless_number'
CONVERT = 'convert'

RANGE = 'range'
LEN = 'len'
CONCAT = 'concat'

KECCAK256 = 'keccak256'
SHA256 = 'sha256'

ASSERT_MODIFIABLE = 'assert_modifiable'
CLEAR = 'clear'
SELFDESTRUCT = 'selfdestruct'
SEND = 'send'

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
CONFIG_NO_OVERFLOWS = 'no_overflows'

INTERFACE = 'interface'

PURE = 'pure'
NOT_ALLOWED_IN_PURE = [MSG, BLOCK, TX]

IMPLIES = 'implies'
FORALL = 'forall'
SUM = 'sum'
RESULT = 'result'
STORAGE = 'storage'
OLD = 'old'
ISSUED = 'issued'
SENT = 'sent'
RECEIVED = 'received'
ACCESSIBLE = 'accessible'
REORDER_INDEPENDENT = 'reorder_independent'
EVENT = 'event'
SELFDESTRUCT = 'selfdestruct'

SUCCESS = 'success'
SUCCESS_IF_NOT = 'if_not'
SUCCESS_OVERFLOW = 'overflow'
SUCCESS_OUT_OF_GAS = 'out_of_gas'
SUCCESS_SENDER_FAILED = 'sender_failed'
SUCCESS_CONDITIONS = [SUCCESS_OVERFLOW, SUCCESS_OUT_OF_GAS, SUCCESS_SENDER_FAILED]

NOT_ALLOWED_IN_SPEC = [ASSERT_MODIFIABLE, CLEAR, SEND, RAW_CALL]
NOT_ALLOWED_IN_INVARIANT = [*NOT_ALLOWED_IN_SPEC, SUCCESS, RESULT, ISSUED, REORDER_INDEPENDENT, EVENT]
NOT_ALLOWED_IN_CHECK = [*NOT_ALLOWED_IN_SPEC, ACCESSIBLE, RESULT]
NOT_ALLOWED_IN_POSTCONDITION = [*NOT_ALLOWED_IN_SPEC, ACCESSIBLE, EVENT]
NOT_ALLOWED_IN_TRANSITIVE_POSTCONDITION = [*NOT_ALLOWED_IN_INVARIANT, REORDER_INDEPENDENT, ACCESSIBLE]

# Heuristics
WITHDRAW = 'withdraw'
